"""Immutable edit-operation engine.

Edits are stored as operations. Rendering/export applies the stack —
never mutate the original master document.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import (
    Document,
    DocumentPage,
    DocumentStatus,
    EditOperation,
    OperationStatus,
    OperationType,
    TextBlock,
)
from app.schemas.document import EditOperationCreate


class EditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def apply(self, document_id: uuid.UUID, payload: EditOperationCreate) -> EditOperation:
        document = await self._get_document(document_id)
        if document.status not in {DocumentStatus.READY, DocumentStatus.EDITING, DocumentStatus.COMPLETED}:
            raise ValueError(f"Document is not editable in status {document.status.value}")

        try:
            op_type = OperationType(payload.type)
        except ValueError as exc:
            raise ValueError(f"Unsupported operation type: {payload.type}") from exc

        page = await self._get_page(document_id, payload.page)
        block: TextBlock | None = None
        if payload.block_id:
            block = await self._get_block(document_id, payload.block_id)

        # Ambiguity guard for replace without block_id: require unique match
        if op_type == OperationType.REPLACE_TEXT and block is None and payload.old_text:
            matches = await self._find_text_matches(document_id, payload.old_text)
            if len(matches) == 0:
                raise ValueError(f'No matches found for "{payload.old_text}"')
            if len(matches) > 1:
                raise ValueError(
                    f'Multiple matches ({len(matches)}) for "{payload.old_text}". '
                    "Specify block_id or confirm which occurrence."
                )
            block = matches[0]

        bbox = None
        if payload.bbox and len(payload.bbox) == 4:
            bbox = {"x0": payload.bbox[0], "y0": payload.bbox[1], "x1": payload.bbox[2], "y1": payload.bbox[3]}
        elif block is not None:
            bbox = {
                "x0": block.x,
                "y0": block.y,
                "x1": block.x + block.width,
                "y1": block.y + block.height,
            }

        old_value = payload.old_text
        if block is not None and old_value is None:
            old_value = block.text

        # Ignore no-op replaces (same text) so history/export stay clean.
        if (
            op_type == OperationType.REPLACE_TEXT
            and old_value is not None
            and payload.new_text is not None
            and old_value == payload.new_text
        ):
            raise ValueError("Replacement text is unchanged")

        operation = EditOperation(
            document_id=document_id,
            page_id=page.id,
            block_id=block.id if block else None,
            operation_type=op_type,
            old_value=old_value,
            new_value=payload.new_text,
            bbox=bbox,
            status=OperationStatus.APPLIED,
        )
        self.db.add(operation)

        # Update in-memory/normalized text block representation only — not the original file.
        if block is not None and op_type == OperationType.REPLACE_TEXT and payload.new_text is not None:
            block.text = payload.new_text
        elif block is not None and op_type == OperationType.DELETE_TEXT:
            block.text = ""

        document.status = DocumentStatus.EDITING
        await self.db.commit()
        await self.db.refresh(operation)
        return operation

    async def list_operations(self, document_id: uuid.UUID) -> list[EditOperation]:
        result = await self.db.execute(
            select(EditOperation)
            .where(EditOperation.document_id == document_id)
            .order_by(EditOperation.created_at.asc())
        )
        return list(result.scalars().all())

    async def undo_last(self, document_id: uuid.UUID) -> EditOperation:
        result = await self.db.execute(
            select(EditOperation)
            .where(
                EditOperation.document_id == document_id,
                EditOperation.status == OperationStatus.APPLIED,
            )
            .order_by(EditOperation.created_at.desc())
            .limit(1)
        )
        operation = result.scalar_one_or_none()
        if operation is None:
            raise LookupError("No applied operations to undo")

        if operation.block_id and operation.old_value is not None:
            block_result = await self.db.execute(
                select(TextBlock).where(TextBlock.id == operation.block_id)
            )
            block = block_result.scalar_one_or_none()
            if block is not None:
                block.text = operation.old_value

        operation.status = OperationStatus.UNDONE
        await self.db.commit()
        await self.db.refresh(operation)
        return operation

    async def redo_last(self, document_id: uuid.UUID) -> EditOperation:
        result = await self.db.execute(
            select(EditOperation)
            .where(
                EditOperation.document_id == document_id,
                EditOperation.status == OperationStatus.UNDONE,
            )
            .order_by(EditOperation.created_at.desc())
            .limit(1)
        )
        operation = result.scalar_one_or_none()
        if operation is None:
            raise LookupError("No undone operations to redo")

        if operation.block_id and operation.new_value is not None:
            block_result = await self.db.execute(
                select(TextBlock).where(TextBlock.id == operation.block_id)
            )
            block = block_result.scalar_one_or_none()
            if block is not None:
                block.text = operation.new_value

        operation.status = OperationStatus.APPLIED
        await self.db.commit()
        await self.db.refresh(operation)
        return operation

    async def _get_document(self, document_id: uuid.UUID) -> Document:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            raise LookupError("Document not found")
        return document

    async def _get_page(self, document_id: uuid.UUID, page_number: int) -> DocumentPage:
        result = await self.db.execute(
            select(DocumentPage).where(
                DocumentPage.document_id == document_id,
                DocumentPage.page_number == page_number,
            )
        )
        page = result.scalar_one_or_none()
        if page is None:
            raise LookupError(f"Page {page_number} not found")
        return page

    async def _get_block(self, document_id: uuid.UUID, block_id: uuid.UUID) -> TextBlock:
        result = await self.db.execute(
            select(TextBlock).where(TextBlock.document_id == document_id, TextBlock.id == block_id)
        )
        block = result.scalar_one_or_none()
        if block is None:
            raise LookupError("Text block not found")
        return block

    async def _find_text_matches(self, document_id: uuid.UUID, text: str) -> list[TextBlock]:
        result = await self.db.execute(
            select(TextBlock).where(TextBlock.document_id == document_id, TextBlock.text == text)
        )
        return list(result.scalars().all())
