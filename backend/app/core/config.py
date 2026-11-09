import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND = Path(__file__).resolve().parents[2]
_REPO = _BACKEND.parent
_LIBPQ_ONLY_PARAMS = {"sslmode", "channel_binding"}
_APP_ENV = os.environ.get("APP_ENV", "local").strip().lower()
# local: .env.local only (SQLite unless that file sets a database).
# dev/cloud: .env.dev (Neon). npm run backend:dev sets APP_ENV=dev.
_ENV_FILES = (
    (str(_REPO / ".env.dev"),)
    if _APP_ENV in {"dev", "cloud"}
    else (str(_REPO / ".env.local"), str(_BACKEND / ".env"))
)


def _to_async_url(url: str) -> str:
    """Turn a Neon/libpq URL into the asyncpg URL SQLAlchemy expects."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    if not url.startswith("postgresql://"):
        return url
    parts = urlsplit(url)
    query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key not in _LIBPQ_ONLY_PARAMS]
    return urlunsplit(("postgresql+asyncpg", parts.netloc, parts.path, urlencode(query), ""))


def _to_sync_url(url: str) -> str:
    if url.startswith("postgresql+asyncpg://"):
        url = "postgresql://" + url[len("postgresql+asyncpg://") :]
    elif url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILES,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Document Text Correction Engine"
    api_prefix: str = "/api/v1"
    debug: bool = True

    # Local default: SQLite (no Postgres required). Neon sets DATABASE_URL in production.
    database_url: str = f"sqlite+aiosqlite:///{(_BACKEND / 'storage' / 'docedit.db').as_posix()}"
    database_url_sync: str = f"sqlite:///{(_BACKEND / 'storage' / 'docedit.db').as_posix()}"
    database_url_unpooled: str = ""


    cors_origins: str = "http://localhost:4200,http://127.0.0.1:4200"

    storage_root: Path = _BACKEND / "storage"
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

    @model_validator(mode="after")
    def normalize_database_urls(self) -> "Settings":
        raw_url = self.database_url
        self.database_url = _to_async_url(raw_url)
        if self.database_url.startswith("postgresql") and self.database_url_sync.startswith("sqlite"):
            direct = self.database_url_unpooled or raw_url
            self.database_url_sync = _to_sync_url(direct)
        else:
            self.database_url_sync = _to_sync_url(self.database_url_sync)
        return self

    @property
    def uses_pooled_postgres(self) -> bool:
        return self.database_url.startswith("postgresql") and "-pooler" in self.database_url

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
