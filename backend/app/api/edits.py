from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.document import EditOperationCreate, EditOperationResponse
from app.services.edit_service import EditService

router = APIRouter(prefix="/documents/{document_id}/edits", tags=["edits"])


def _to_response(op) -> EditOperationResponse:
    return EditOperationResponse(
        id=op.id,
        document_id=op.document_id,
        operation_type=op.operation_type.value,
        old_value=op.old_value,
        new_value=op.new_value,
        bbox=op.bbox,
        status=op.status.value,
        created_at=op.created_at,
    )


@router.post("", response_model=EditOperationResponse, status_code=status.HTTP_201_CREATED)
async def create_edit(
    document_id: UUID,
    payload: EditOperationCreate,
    db: AsyncSession = Depends(get_db),
) -> EditOperationResponse:
    service = EditService(db)
    try:
        op = await service.apply(document_id, payload)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return _to_response(op)


@router.get("", response_model=list[EditOperationResponse])
async def list_edits(document_id: UUID, db: AsyncSession = Depends(get_db)) -> list[EditOperationResponse]:
    service = EditService(db)
    ops = await service.list_operations(document_id)
    return [_to_response(op) for op in ops]


@router.post("/undo", response_model=EditOperationResponse)
async def undo_edit(document_id: UUID, db: AsyncSession = Depends(get_db)) -> EditOperationResponse:
    service = EditService(db)
    try:
        op = await service.undo_last(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(op)


@router.post("/redo", response_model=EditOperationResponse)
async def redo_edit(document_id: UUID, db: AsyncSession = Depends(get_db)) -> EditOperationResponse:
    service = EditService(db)
    try:
        op = await service.redo_last(document_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return _to_response(op)
