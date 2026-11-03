import re
import uuid
from pathlib import Path

import aiofiles

from app.core.config import Settings, get_settings


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    name = re.sub(r"[^\w.\- ()\[\]]+", "_", name, flags=re.UNICODE)
    return name[:200] or "upload"


class StorageService:
    """Local object-storage stand-in: originals / working / exports are never mixed."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        for path in (
            self.settings.originals_dir,
            self.settings.working_dir,
            self.settings.exports_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    def build_original_key(self, document_id: uuid.UUID, filename: str) -> str:
        safe = sanitize_filename(filename)
        return f"{document_id}/{uuid.uuid4().hex}_{safe}"

    def original_path(self, storage_key: str) -> Path:
        return self.settings.originals_dir / storage_key

    def working_path(self, storage_key: str) -> Path:
        return self.settings.working_dir / storage_key

    def export_path(self, storage_key: str) -> Path:
        return self.settings.exports_dir / storage_key

    async def save_original(self, storage_key: str, data: bytes) -> Path:
        path = self.original_path(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        return path

    def resolve_original(self, storage_key: str) -> Path:
        path = self.original_path(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"Original not found: {storage_key}")
        return path
