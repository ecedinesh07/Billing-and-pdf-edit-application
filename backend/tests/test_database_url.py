from app.core.config import _to_async_url, _to_sync_url


def test_neon_pooled_url_becomes_asyncpg_without_libpq_params() -> None:
    raw = (
        "postgresql://user:secret@ep-example-pooler.c-9.us-east-2.aws.neon.tech/neondb"
        "?channel_binding=require&sslmode=require"
    )
    assert _to_async_url(raw) == (
        "postgresql+asyncpg://user:secret@ep-example-pooler.c-9.us-east-2.aws.neon.tech/neondb"
    )


def test_sqlite_url_is_unchanged() -> None:
    url = "sqlite+aiosqlite:///storage/docedit.db"
    assert _to_async_url(url) == url
    assert _to_sync_url(url) == url
