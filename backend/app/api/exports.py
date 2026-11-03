from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.export_service import ExportService

router = APIRouter(prefix="/documents/{document_id}/exports", tags=["exports"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_export(
    document_id: UUID,
    output_format: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    service = ExportService(db)
    try:
        job = await service.export(document_id, output_format)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return {
        "export_id": str(job.id),
        "document_id": str(document_id),
        "status": job.status,
        "output_format": job.output_format,
        "error_message": job.error_message,
    }


@router.get("/{export_id}/download")
async def download_export(
    document_id: UUID,
    export_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    service = ExportService(db)
    try:
        job = await service.get_job(document_id, export_id)
        path = service.resolve_export_file(job)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return FileResponse(path, filename=path.name)
