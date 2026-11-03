from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.document import UploadResponse
from app.services.document_service import DocumentService

router = APIRouter(prefix="/uploads", tags=["uploads"])


@router.post("", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    data = await file.read()
    service = DocumentService(db)
    try:
        document = await service.create_from_upload(
            filename=file.filename or "upload",
            content_type=file.content_type,
            data=data,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    return UploadResponse(
        document_id=document.id,
        status=document.status.value,
        original_filename=document.original_filename,
        mime_type=document.mime_type,
        message="Upload stored; original preserved. Processing completed or failed as indicated by status.",
    )
