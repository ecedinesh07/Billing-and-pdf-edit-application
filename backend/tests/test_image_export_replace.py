from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.render_service import AppliedEdit, RenderService


def test_png_export_replaces_text_region(tmp_path: Path):
    original = tmp_path / "original.png"
    exported = tmp_path / "exported.png"

    img = Image.new("RGB", (400, 120), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 28)
    except OSError:
        font = ImageFont.load_default()
    draw.text((20, 40), "DIVYA", fill=(0, 0, 0), font=font)
    img.save(original)

    RenderService().render(
        original=original,
        dest=exported,
        mime_type="image/png",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value="DIVYA",
                new_value="BABY OF DIVYA",
                bbox={"x0": 20, "y0": 40, "x1": 120, "y1": 75},
                font_size=28,
                block_id="b1",
            )
        ],
    )

    assert exported.exists()
    assert exported.stat().st_size > 0
    # Region should no longer match the original pixel-for-pixel (localized change).
    with Image.open(original) as a, Image.open(exported) as b:
        assert list(a.getdata()) != list(b.getdata())
