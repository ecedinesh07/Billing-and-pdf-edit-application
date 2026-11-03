from pathlib import Path

import fitz

from app.services.render_service import AppliedEdit, RenderService


def test_pdf_replace_text_is_written_to_export(tmp_path: Path):
    original = tmp_path / "original.pdf"
    exported = tmp_path / "exported.pdf"

    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((50, 80), "Application APP0259 Requisition Response", fontsize=12)
    doc.save(original.as_posix())
    doc.close()

    edits = [
        AppliedEdit(
            operation_type="replace_text",
            page_number=1,
            old_value="Application APP0259 Requisition Response",
            new_value="Application APP0259 Requisition Responseddd",
            bbox={"x0": 50, "y0": 65, "x1": 360, "y1": 85},
            font_size=12,
            font_family="helv",
        )
    ]

    RenderService().render(
        original=original,
        dest=exported,
        mime_type="application/pdf",
        edits=edits,
    )

    out = fitz.open(exported)
    try:
        text = out[0].get_text()
    finally:
        out.close()

    assert "Responseddd" in text
    assert "Requisition Response\n" not in text or "Responseddd" in text
