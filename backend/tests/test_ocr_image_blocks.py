from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.services.ocr_service import OcrService


def test_ocr_extracts_text_from_png(tmp_path: Path):
    image_path = tmp_path / "bill.png"
    img = Image.new("RGB", (640, 200), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 70), "INVOICE TOTAL 2500", fill=(0, 0, 0), font=font)
    img.save(image_path)

    blocks = OcrService().extract(image_path)
    assert blocks, "OCR should detect at least one text block"
    joined = " ".join(b.text for b in blocks).upper()
    assert "INVOICE" in joined or "2500" in joined
    assert all(b.confidence is not None for b in blocks)
