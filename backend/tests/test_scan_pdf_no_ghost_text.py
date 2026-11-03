from pathlib import Path

import fitz

from app.services.render_service import AppliedEdit, RenderService


def test_image_backed_pdf_clears_old_pixels_before_redraw(tmp_path: Path):
    originals = list(Path("storage/originals").rglob("*Baby of DD receipt.pdf"))
    if not originals:
        return  # sample upload not present in CI

    original = originals[0]
    exported = tmp_path / "exported.pdf"

    src = fitz.open(original)
    try:
        page = src[0]
        # Name value area on this hospital bill (OCR-fragmented spans)
        cover = fitz.Rect(84.0, 114.0, 160.0, 125.0)
        style_span = None
        for block in page.get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    if "DIVYA" in (span.get("text") or ""):
                        style_span = span
                        cover |= fitz.Rect(span["bbox"])
        assert style_span is not None
        bbox = cover
    finally:
        src.close()

    RenderService().render(
        original=original,
        dest=exported,
        mime_type="application/pdf",
        edits=[
            AppliedEdit(
                operation_type="replace_text",
                page_number=1,
                old_value="DIVYA",
                new_value="Baby Of DIVYA DINESH",
                bbox={"x0": bbox.x0, "y0": bbox.y0, "x1": bbox.x1, "y1": bbox.y1},
                font_family="ArialMT",
                block_id="name-1",
            )
        ],
    )

    out = fitz.open(exported)
    try:
        text = out[0].get_text().replace("\n", " ").replace("\xa0", " ")
        assert "Baby Of DIVYA DINESH" in text

        # The redact region should not keep dense dark ink from the old scan underneath.
        check = fitz.Rect(bbox.x0, bbox.y0, min(bbox.x0 + 40, bbox.x1), bbox.y1)
        pix = out[0].get_pixmap(clip=check, alpha=False)
        samples = pix.samples
        # Count very dark pixels; after clean redraw these should be limited to new glyphs.
        dark = sum(
            1
            for i in range(0, len(samples), 3)
            if (samples[i] + samples[i + 1] + samples[i + 2]) / 3 < 40
        )
        # Sanity: page still has content, but not a fully black ghost rectangle.
        assert dark < pix.width * pix.height * 0.55
    finally:
        out.close()
