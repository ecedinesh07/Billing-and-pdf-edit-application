from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.document import DocumentResponse, DocumentStatusResponse, NormalizedDocument
from app.services.document_service import DocumentService

router = APIRouter(prefix="/documents", tags=["documents"])


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(document_id: UUID, db: AsyncSession = Depends(get_db)) -> DocumentResponse:
    service = DocumentService(db)
    try:
        document = await service.get_document(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DocumentResponse(
        id=document.id,
        original_filename=document.original_filename,
        source_type=document.source_type.value,
        mime_type=document.mime_type,
        page_count=document.page_count,
        status=document.status.value,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/{document_id}/status", response_model=DocumentStatusResponse)
async def get_status(document_id: UUID, db: AsyncSession = Depends(get_db)) -> DocumentStatusResponse:
    service = DocumentService(db)
    try:
        document = await service.get_document(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return DocumentStatusResponse(
        document_id=document.id,
        status=document.status.value,
        page_count=document.page_count,
        source_type=document.source_type.value,
        error_message=document.error_message,
    )


@router.get("/{document_id}/model", response_model=NormalizedDocument)
async def get_normalized_model(
    document_id: UUID, db: AsyncSession = Depends(get_db)
) -> NormalizedDocument:
    service = DocumentService(db)
    try:
        payload = await service.get_normalized(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return NormalizedDocument(**payload)


@router.get("/{document_id}/pages/{page_number}/preview")
async def get_page_preview(
    document_id: UUID,
    page_number: int,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    service = DocumentService(db)
    try:
        path = await service.get_page_preview_path(document_id, page_number)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    media = "image/png"
    suffix = path.suffix.lower()
    if suffix in {".jpg", ".jpeg"}:
        media = "image/jpeg"
    elif suffix == ".webp":
        media = "image/webp"
    return FileResponse(
        path,
        media_type=media,
        filename=path.name,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate",
            "Pragma": "no-cache",
        },
    )
