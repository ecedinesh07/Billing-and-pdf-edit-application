from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api import documents, edits, exports, uploads
from app.core.config import get_settings
from app.core.database import Base, engine
from app.models import document as _models  # noqa: F401 — register metadata


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    for path in (settings.originals_dir, settings.working_dir, settings.exports_dir):
        path.mkdir(parents=True, exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(uploads.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(edits.router, prefix=prefix)
    app.include_router(exports.router, prefix=prefix)

    @app.get("/")
    @app.get("/health")
    async def health() -> dict[str, str]:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok"}

    return app


app = create_app()
