from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.render_service import AppliedEdit, GlyphSource, RenderService


def test_replacement_reuses_original_ink_glyphs(tmp_path: Path):
    original = tmp_path / "bill.png"
    exported = tmp_path / "out.png"

    img = Image.new("RGB", (640, 180), color=(236, 220, 190))
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype("C:/Windows/Fonts/cour.ttf", 32)
    text = "1526533"
    draw.text((50, 70), text, fill=(35, 35, 35), font=font)
    bbox = draw.textbbox((50, 70), text, font=font)
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
                new_value="3356251",  # permutation of same digits → full glyph coverage
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                block_id="r1",
            )
        ],
        glyph_sources=[
            GlyphSource(
                text=text,
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
            )
        ],
    )

    assert exported.exists()
    with Image.open(original) as src, Image.open(exported) as out:
        assert list(src.getdata()) != list(out.getdata())
        # Paper near the line should remain warm (not a gray UI plate).
        sample = out.getpixel((bbox[0] - 2, bbox[1] - 2))
        assert sample[0] > 180
