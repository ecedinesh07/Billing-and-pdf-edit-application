from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.render_service import AppliedEdit, RenderService


def test_live_preview_image_differs_from_original_after_replace(tmp_path: Path):
    """Editor preview must show localized edits, not the pristine original."""
    original = tmp_path / "bill.png"
    preview = tmp_path / "live_preview.png"

    img = Image.new("RGB", (420, 140), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((24, 50), "Dummy PDF file", fill=(0, 0, 0), font=font)
    bbox = draw.textbbox((24, 50), "Dummy PDF file", font=font)
    img.save(original)

    RenderService().render(
        original=original,
        dest=preview,
        mime_type="image/png",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value="Dummy PDF file",
                new_value="Dummy PDF file gg",
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                font_size=28,
                block_id="b1",
            )
        ],
    )

    assert preview.exists()
    with Image.open(original) as a, Image.open(preview) as b:
        assert list(a.getdata()) != list(b.getdata())
