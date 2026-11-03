"""Image helpers. Originals are never overwritten."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image


@dataclass
class ImageMeta:
    width: int
    height: int
    mode: str


class ImageService:
    def inspect(self, path: Path) -> ImageMeta:
        with Image.open(path) as img:
            return ImageMeta(width=img.width, height=img.height, mode=img.mode)

    def create_working_copy(self, source: Path, dest: Path) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(source) as img:
            img.save(dest)
        return dest
