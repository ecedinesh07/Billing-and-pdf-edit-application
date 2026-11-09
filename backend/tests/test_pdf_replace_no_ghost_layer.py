from pathlib import Path

import fitz

from app.services.render_service import AppliedEdit, RenderService


def test_digital_pdf_replace_does_not_leave_old_glyphs(tmp_path: Path):
    original = tmp_path / "form.pdf"
    exported = tmp_path / "out.pdf"

    doc = fitz.open()
    page = doc.new_page(width=400, height=200)
    page.insert_text((40, 80), "16 October 2026, 9:38 PM", fontsize=12, fontname="helv", color=(0, 0, 0))
    doc.save(original.as_posix())
    doc.close()

    src = fitz.open(original)
    hit = src[0].search_for("16 October 2026, 9:38 PM")[0]
    src.close()

    RenderService().render(
        original=original,
        dest=exported,
        mime_type="application/pdf",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value="16 October 2026, 9:38 PM",
                new_value="16 October 2026, 9:38 PMkk",
                bbox={"x0": hit.x0, "y0": hit.y0, "x1": hit.x1, "y1": hit.y1},
                block_id="date-1",
            )
        ],
    )

    out = fitz.open(exported)
    try:
        text = out[0].get_text().replace("\xa0", " ").replace("\n", " ")
        assert "16 October 2026, 9:38 PMkk" in text
        # Old value without the suffix must not appear as a second ghost string.
        assert text.count("16 October 2026, 9:38 PM") == 1
    finally:
        out.close()
