from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Document Text Correction Engine"
    api_prefix: str = "/api/v1"
    debug: bool = True

    # Local default: SQLite (no Postgres required). Override with PostgreSQL in production.
    database_url: str = f"sqlite+aiosqlite:///{(Path(__file__).resolve().parents[2] / 'storage' / 'docedit.db').as_posix()}"
    database_url_sync: str = f"sqlite:///{(Path(__file__).resolve().parents[2] / 'storage' / 'docedit.db').as_posix()}"


    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"

    storage_root: Path = Path(__file__).resolve().parents[2] / "storage"
    max_upload_bytes: int = 20 * 1024 * 1024  # 20 MB (open decision — adjustable)
    max_pdf_pages: int = 50
    allowed_mime_types: set[str] = {
        "application/pdf",
        "image/jpeg",
        "image/png",
    }
    allowed_extensions: set[str] = {".pdf", ".jpg", ".jpeg", ".png"}

    # Temporary processing retention (hours)
    temp_file_retention_hours: int = 24

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def originals_dir(self) -> Path:
        return self.storage_root / "originals"

    @property
    def working_dir(self) -> Path:
        return self.storage_root / "working"

    @property
    def exports_dir(self) -> Path:
        return self.storage_root / "exports"


@lru_cache
def get_settings() -> Settings:
    return Settings()
