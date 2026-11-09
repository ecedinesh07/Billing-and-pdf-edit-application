from pathlib import Path

import fitz

from app.services.render_service import AppliedEdit, RenderService


def test_replace_reuses_embedded_liberation_serif(tmp_path: Path):
    originals = list(Path("storage/originals").rglob("*Lodgement Notice*.pdf"))
    if not originals:
        # Synthetic fallback when sample upload is absent.
        original = tmp_path / "orig.pdf"
        doc = fitz.open()
        page = doc.new_page(width=500, height=200)
        page.insert_text((80, 80), "Lodgement Notice", fontname="tiro", fontsize=28)
        doc.save(original.as_posix())
        doc.close()
    else:
        original = originals[0]

    exported = tmp_path / "exported.pdf"
    # Read original span style for assertion target
    src = fitz.open(original)
    try:
        span = None
        for block in src[0].get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for s in line.get("spans", []):
                    if s.get("text", "").strip() == "Lodgement Notice" and float(s.get("size", 0)) >= 20:
                        span = s
                        break
        assert span is not None
        bbox = span["bbox"]
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
                old_value="Lodgement Notice",
                new_value="Lodgement Notice new",
                bbox={"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]},
                font_size=28,
                font_family="LiberationSerif",
            )
        ],
    )

    out = fitz.open(exported)
    try:
        text = out[0].get_text().replace("\xa0", " ")
        assert "Lodgement Notice new" in text

        # Replacement span should keep serif family and ~28pt size (not Helvetica).
        replaced = None
        for block in out[0].get_text("dict")["blocks"]:
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for s in line.get("spans", []):
                    if "Lodgement Notice new" in (s.get("text") or "").replace("\xa0", " "):
                        replaced = s
                        break
        assert replaced is not None
        font = (replaced.get("font") or "").lower()
        assert "helv" not in font
        assert "noto" not in font
        assert abs(float(replaced.get("size") or 0) - float(span.get("size") or 28.0)) < 1.5
    finally:
        out.close()
