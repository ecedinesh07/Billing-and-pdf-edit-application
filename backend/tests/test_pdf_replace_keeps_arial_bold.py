from pathlib import Path

import fitz

from app.services.render_service import AppliedEdit, RenderService


def test_dummy_pdf_keeps_arial_bold_weight_and_size(tmp_path: Path):
    originals = list(Path("storage/originals").rglob("*dummy.pdf"))
    if originals:
        original = originals[0]
    else:
        original = tmp_path / "dummy.pdf"
        doc = fitz.open()
        page = doc.new_page(width=400, height=200)
        page.insert_text((56, 84), "Dummy PDF file", fontsize=16.1, fontname="hebo")
        doc.save(original.as_posix())
        doc.close()

    src = fitz.open(original)
    try:
        span = None
        for block in src[0].get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for s in line.get("spans", []):
                    if "Dummy PDF file" in (s.get("text") or ""):
                        span = s
                        break
        assert span is not None
        bbox = span["bbox"]
        original_size = float(span.get("size") or 0)
        original_font = (span.get("font") or "").lower()
    finally:
        src.close()

    exported = tmp_path / "out.pdf"
    RenderService().render(
        original=original,
        dest=exported,
        mime_type="application/pdf",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value="Dummy PDF file",
                new_value="Dummy PDF filess",
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                block_id="dummy-1",
            )
        ],
    )

    out = fitz.open(exported)
    try:
        replaced = None
        for block in out[0].get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for s in line.get("spans", []):
                    if "Dummy PDF filess" in (s.get("text") or "").replace("\xa0", " "):
                        replaced = s
                        break
        assert replaced is not None
        font = (replaced.get("font") or "").lower()
        assert "noto" not in font
        assert "helv" not in font or "bold" in original_font
        if "bold" in original_font or "arial" in original_font:
            assert "arial" in font
            assert "bold" in font
        assert abs(float(replaced.get("size") or 0) - original_size) < 0.6
    finally:
        out.close()
