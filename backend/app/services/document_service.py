"""Document upload, classification, and normalized model building."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import Settings, get_settings
from app.models.document import (
    Document,
    DocumentPage,
    DocumentStatus,
    SourceType,
    TextBlock,
)
from app.services.image_service import ImageService
from app.services.ocr_service import OcrService
from app.services.pdf_service import PdfService
from app.services.storage_service import StorageService, sanitize_filename


class DocumentService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        storage: StorageService | None = None,
        pdf: PdfService | None = None,
        images: ImageService | None = None,
        ocr: OcrService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.storage = storage or StorageService(self.settings)
        self.pdf = pdf or PdfService()
        self.images = images or ImageService()
        self.ocr = ocr or OcrService()

    def validate_upload(self, filename: str, content_type: str | None, size: int) -> tuple[str, str]:
        if size <= 0:
            raise ValueError("Empty file is not allowed")
        if size > self.settings.max_upload_bytes:
            raise ValueError(f"File exceeds max size of {self.settings.max_upload_bytes} bytes")

        safe_name = sanitize_filename(filename)
        ext = Path(safe_name).suffix.lower()
        if ext not in self.settings.allowed_extensions:
            raise ValueError(f"Unsupported file extension: {ext}")

        mime = (content_type or "").split(";")[0].strip().lower()
        # Browsers sometimes send application/octet-stream; infer from extension as fallback.
        if mime not in self.settings.allowed_mime_types:
            mime = {
                ".pdf": "application/pdf",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
            }.get(ext, mime)
        if mime not in self.settings.allowed_mime_types:
            raise ValueError(f"Unsupported MIME type: {mime}")

        return safe_name, mime

    async def create_from_upload(
        self,
        *,
        filename: str,
        content_type: str | None,
        data: bytes,
        user_id: uuid.UUID | None = None,
    ) -> Document:
        safe_name, mime = self.validate_upload(filename, content_type, len(data))
        document_id = uuid.uuid4()
        storage_key = self.storage.build_original_key(document_id, safe_name)

        await self.storage.save_original(storage_key, data)

        document = Document(
            id=document_id,
            user_id=user_id,
            original_filename=safe_name,
            mime_type=mime,
            original_storage_key=storage_key,
            status=DocumentStatus.PROCESSING,
            source_type=SourceType.UNKNOWN,
            page_count=0,
        )
        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        try:
            await self._analyze_and_index(document)
        except Exception as exc:  # noqa: BLE001 — surface as document failure status
            document.status = DocumentStatus.FAILED
            document.error_message = str(exc)
            await self.db.commit()
            await self.db.refresh(document)
            return document

        return await self.get_document(document.id)

    async def _analyze_and_index(self, document: Document) -> None:
        path = self.storage.resolve_original(document.original_storage_key)

        if document.mime_type == "application/pdf":
            await self._index_pdf(document, path)
        else:
            await self._index_image(document, path)

        document.status = DocumentStatus.READY
        await self.db.commit()

    async def _index_pdf(self, document: Document, path: Path) -> None:
        analysis = self.pdf.analyze(path)
        if analysis.page_count > self.settings.max_pdf_pages:
            raise ValueError(f"PDF exceeds max page count ({self.settings.max_pdf_pages})")

        document.page_count = analysis.page_count
        document.source_type = (
            SourceType.TEXT_PDF if analysis.is_text_based else SourceType.SCANNED_PDF
        )

        for page in analysis.pages:
            page_row = DocumentPage(
                document_id=document.id,
                page_number=page.page_number,
                width=page.width,
                height=page.height,
            )
            self.db.add(page_row)
            await self.db.flush()

            if analysis.is_text_based:
                for block in page.blocks:
                    self.db.add(
                        TextBlock(
                            document_id=document.id,
                            page_id=page_row.id,
                            text=block.text,
                            x=block.x0,
                            y=block.y0,
                            width=block.x1 - block.x0,
                            height=block.y1 - block.y0,
                            font_family=block.font_family,
                            font_size=block.font_size,
                            rotation=block.rotation,
                            language=None,
                            direction="ltr",
                            ocr_confidence=None,
                        )
                    )
            else:
                # Scanned PDF: render page to working storage then OCR (pluggable).
                preview_key = f"{document.id}/page_{page.page_number}.png"
                preview_path = self.storage.working_path(preview_key)
                self.pdf.render_page_preview(path, page.page_number, preview_path)
                page_row.preview_storage_key = preview_key
                document.status = DocumentStatus.OCR_RUNNING
                await self.db.flush()
                for ocr_block in self.ocr.extract(preview_path, page.page_number):
                    self.db.add(self._text_block_from_ocr(document.id, page_row.id, ocr_block))

    async def _index_image(self, document: Document, path: Path) -> None:
        meta = self.images.inspect(path)
        document.page_count = 1
        document.source_type = SourceType.IMAGE
        document.status = DocumentStatus.OCR_RUNNING
        await self.db.flush()

        working_key = f"{document.id}/working{Path(document.original_filename).suffix.lower()}"
        self.images.create_working_copy(path, self.storage.working_path(working_key))

        page_row = DocumentPage(
            document_id=document.id,
            page_number=1,
            width=float(meta.width),
            height=float(meta.height),
            preview_storage_key=working_key,
        )
        self.db.add(page_row)
        await self.db.flush()

        for ocr_block in self.ocr.extract(self.storage.working_path(working_key), 1):
            self.db.add(self._text_block_from_ocr(document.id, page_row.id, ocr_block))

    @staticmethod
    def _text_block_from_ocr(document_id, page_id, ocr_block) -> TextBlock:
        return TextBlock(
            document_id=document_id,
            page_id=page_id,
            text=ocr_block.text,
            x=ocr_block.x0,
            y=ocr_block.y0,
            width=ocr_block.x1 - ocr_block.x0,
            height=ocr_block.y1 - ocr_block.y0,
            font_size=ocr_block.font_size,
            ocr_confidence=ocr_block.confidence,
            language=ocr_block.language,
            direction="ltr",
        )

    async def get_document(self, document_id: uuid.UUID) -> Document:
        result = await self.db.execute(select(Document).where(Document.id == document_id))
        document = result.scalar_one_or_none()
        if document is None:
            raise LookupError("Document not found")
        return document

    async def get_page_preview_path(self, document_id: uuid.UUID, page_number: int) -> Path:
        """Return a raster preview path for the editor background (never the master original).

        When edits are applied, returns a live preview that matches export rendering.
        """
        # Prefer edited live preview so the left pane matches download output.
        from app.services.export_service import ExportService

        live = await ExportService(self.db, self.settings, self.storage).live_page_preview(
            document_id, page_number
        )
        if live is not None:
            return live

        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.pages))
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise LookupError("Document not found")

        page = next((p for p in document.pages if p.page_number == page_number), None)
        if page is None:
            raise LookupError(f"Page {page_number} not found")

        if page.preview_storage_key:
            path = self.storage.working_path(page.preview_storage_key)
            if path.exists():
                return path

        # Text PDFs: render a working preview without touching the original.
        if document.mime_type == "application/pdf":
            preview_key = f"{document.id}/page_{page_number}.png"
            preview_path = self.storage.working_path(preview_key)
            if not preview_path.exists():
                original = self.storage.resolve_original(document.original_storage_key)
                self.pdf.render_page_preview(original, page_number, preview_path)
            page.preview_storage_key = preview_key
            await self.db.commit()
            return preview_path

        # Image docs: fall back to original bytes for display only (read-only).
        return self.storage.resolve_original(document.original_storage_key)

    async def get_normalized(self, document_id: uuid.UUID) -> dict:
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.pages).selectinload(DocumentPage.text_blocks))
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise LookupError("Document not found")

        pages = sorted(document.pages, key=lambda p: p.page_number)
        return {
            "document_id": document.id,
            "source_type": document.source_type.value,
            "status": document.status.value,
            "pages": [
                {
                    "page_number": page.page_number,
                    "width": page.width,
                    "height": page.height,
                    "rotation": page.rotation,
                    "blocks": [
                        {
                            "id": block.id,
                            "type": "text",
                            "text": block.text,
                            "bbox": [
                                block.x,
                                block.y,
                                block.x + block.width,
                                block.y + block.height,
                            ],
                            "language": block.language,
                            "direction": block.direction,
                            "confidence": block.ocr_confidence,
                            "font_family": block.font_family,
                            "font_size": block.font_size,
                            "rotation": block.rotation,
                        }
                        for block in page.text_blocks
                    ],
                }
                for page in pages
            ],
        }
