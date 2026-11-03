from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.render_service import AppliedEdit, RenderService


def test_image_redraw_matches_ink_height_and_applies_spacing(tmp_path: Path):
    original = tmp_path / "style.png"
    exported = tmp_path / "out.png"

    img = Image.new("RGB", (520, 140), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/arialbd.ttf", 34)
    text = "DIVYA DINESH"
    draw.text((30, 45), text, fill=(20, 20, 20), font=font)
    # Approximate ink box from rendered glyphs
    bbox = draw.textbbox((30, 45), text, font=font)
    img.save(original)

    service = RenderService()
    service.render(
        original=original,
        dest=exported,
        mime_type="image/png",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value=text,
                new_value="BABY OF DIVYA",
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                font_size=34,
                block_id="name",
            )
        ],
    )

    assert exported.exists()
    with Image.open(original) as src, Image.open(exported) as out:
        style = service._analyze_image_text_style(
            src.convert("RGB"),
            (bbox[0], bbox[1], bbox[2], bbox[3]),
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value=text,
                new_value="BABY OF DIVYA",
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
            ),
        )
        # Fitted size should be near the original face size / ink height.
        assert abs(style.font_size - 34) <= 10
        assert style.ink_box[2] > style.ink_box[0]
        assert list(src.getdata()) != list(out.getdata())

