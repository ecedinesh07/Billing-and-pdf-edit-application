from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    # Always allow both localhost and 127.0.0.1 for the Angular dev server.
    allow_origins = list(
        dict.fromkeys(
            [
                *settings.cors_origin_list,
                "http://localhost:4200",
                "http://127.0.0.1:4200",
            ]
        )
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    prefix = settings.api_prefix
    app.include_router(uploads.router, prefix=prefix)
    app.include_router(documents.router, prefix=prefix)
    app.include_router(edits.router, prefix=prefix)
    app.include_router(exports.router, prefix=prefix)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
