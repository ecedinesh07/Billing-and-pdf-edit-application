from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.render_service import AppliedEdit, RenderService


def test_receipt_redraw_uses_mono_and_paper_texture(tmp_path: Path):
    original = tmp_path / "receipt.png"
    exported = tmp_path / "out.png"

    # Simulate warm thermal paper + thin mono digits.
    img = Image.new("RGB", (420, 160), color=(236, 220, 190))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/cour.ttf", 28)
    text = "1526533"
    draw.text((40, 60), text, fill=(40, 40, 40), font=font)
    bbox = draw.textbbox((40, 60), text, font=font)
    img.save(original)

    service = RenderService()
    style = service._analyze_image_text_style(
        img.convert("RGB"),
        (bbox[0], bbox[1], bbox[2], bbox[3]),
        AppliedEdit(
            operation_type="replace_text",
            page_number=1,
            old_value=text,
            new_value="9999999",
            bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
        ),
    )
    assert style.mono is True
    assert style.bold is False

    service.render(
        original=original,
        dest=exported,
        mime_type="image/png",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value=text,
                new_value="9999999",
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                block_id="receipt-no",
            )
        ],
    )

    with Image.open(exported) as out:
        # Sample a pixel just outside glyph center — should stay warm paper, not a gray plate.
        px = out.getpixel((bbox[0] - 1, bbox[1] - 1))
        assert px[0] > 180 and px[1] > 160
