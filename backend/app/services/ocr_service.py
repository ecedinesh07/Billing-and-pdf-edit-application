"""Pluggable OCR service.

Engine: RapidOCR (ONNX Runtime) — Apache-2.0, pip-installable, no system Tesseract.
Used for PNG/JPG and scanned PDF page images so text can be selected/edited like text PDFs.

Low-confidence results are retained with `confidence` for UI confirmation (Rule 9).
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass
class OcrBlock:
    text: str
    x0: float
    y0: float
    x1: float
    y1: float
    confidence: float
    language: str | None = None
    font_size: float | None = None


@lru_cache(maxsize=1)
def _get_engine():
    from rapidocr_onnxruntime import RapidOCR

    return RapidOCR()


class OcrService:
    """OCR adapter. Do not treat low confidence as guaranteed truth."""

    engine_name: str = "rapidocr"

    def extract(self, image_path: Path, page_number: int = 1) -> list[OcrBlock]:
        _ = page_number
        if not image_path.exists():
            return []

        try:
            engine = _get_engine()
            result, _elapsed = engine(str(image_path))
        except Exception:  # noqa: BLE001 — surface empty OCR rather than failing upload
            return []

        if not result:
            return []

        blocks: list[OcrBlock] = []
        for item in result:
            # RapidOCR item: [box_points, text, score]
            if not item or len(item) < 3:
                continue
            box, text, score = item[0], item[1], item[2]
            text = (text or "").strip()
            if not text:
                continue
            xs = [float(p[0]) for p in box]
            ys = [float(p[1]) for p in box]
            x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
            height = max(1.0, y1 - y0)
            conf = float(score)
            # Normalize if engine returns 0-100
            if conf > 1.0:
                conf = conf / 100.0
            blocks.append(
                OcrBlock(
                    text=text,
                    x0=x0,
                    y0=y0,
                    x1=x1,
                    y1=y1,
                    confidence=conf,
                    language=None,
                    font_size=height * 0.8,
                )
            )
        return blocks
