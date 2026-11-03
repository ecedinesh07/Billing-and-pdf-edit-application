"""PDF classification and text extraction via PyMuPDF.

Preserves original files; only reads for analysis / text-layer extraction.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import fitz  # PyMuPDF


@dataclass
class ExtractedBlock:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    font_family: str | None = None
    font_size: float | None = None
    rotation: float = 0.0


@dataclass
class ExtractedPage:
    page_number: int
    width: float
    height: float
    blocks: list[ExtractedBlock]
    has_text: bool


@dataclass
class PdfAnalysis:
    page_count: int
    is_text_based: bool
    pages: list[ExtractedPage]


class PdfService:
    def analyze(self, path: Path) -> PdfAnalysis:
        doc = fitz.open(path)
        try:
            pages: list[ExtractedPage] = []
            text_pages = 0
            for index, page in enumerate(doc):
                blocks = self._extract_blocks(page)
                has_text = any(b.text.strip() for b in blocks)
                if has_text:
                    text_pages += 1
                rect = page.rect
                pages.append(
                    ExtractedPage(
                        page_number=index + 1,
                        width=float(rect.width),
                        height=float(rect.height),
                        blocks=blocks,
                        has_text=has_text,
                    )
                )
            # Prefer text extraction when most pages have selectable text
            is_text_based = text_pages > 0 and text_pages >= max(1, len(pages) // 2)
            return PdfAnalysis(page_count=len(pages), is_text_based=is_text_based, pages=pages)
        finally:
            doc.close()

    def _extract_blocks(self, page: fitz.Page) -> list[ExtractedBlock]:
        result: list[ExtractedBlock] = []
        raw = page.get_text("dict")
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                text = "".join(span.get("text", "") for span in spans).strip()
                if not text:
                    continue
                xs = [span["bbox"][0] for span in spans]
                ys = [span["bbox"][1] for span in spans]
                x1s = [span["bbox"][2] for span in spans]
                y1s = [span["bbox"][3] for span in spans]
                first = spans[0]
                result.append(
                    ExtractedBlock(
                        text=text,
                        x0=float(min(xs)),
                        y0=float(min(ys)),
                        x1=float(max(x1s)),
                        y1=float(max(y1s)),
                        font_family=first.get("font"),
                        font_size=float(first.get("size", 0)) or None,
                        rotation=0.0,
                    )
                )
        return result

    def render_page_preview(self, path: Path, page_number: int, out_path: Path, dpi: int = 144) -> None:
        doc = fitz.open(path)
        try:
            page = doc[page_number - 1]
            pix = page.get_pixmap(dpi=dpi)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            pix.save(out_path.as_posix())
        finally:
            doc.close()
