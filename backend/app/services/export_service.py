"""Export derived documents. Original remains untouched."""

from __future__ import annotations

import hashlib
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
    EditOperation,
    ExportJob,
    OperationStatus,
    TextBlock,
)
from app.services.render_service import AppliedEdit, GlyphSource, RenderService
from app.services.storage_service import StorageService


class ExportService:
    def __init__(
        self,
        db: AsyncSession,
        settings: Settings | None = None,
        storage: StorageService | None = None,
        renderer: RenderService | None = None,
    ) -> None:
        self.db = db
        self.settings = settings or get_settings()
        self.storage = storage or StorageService(self.settings)
        self.renderer = renderer or RenderService()

    async def export(self, document_id: uuid.UUID, output_format: str | None = None) -> ExportJob:
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.pages).selectinload(DocumentPage.text_blocks))
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise LookupError("Document not found")

        fmt = (output_format or self._default_format(document.mime_type)).lower()
        job = ExportJob(document_id=document_id, output_format=fmt, status="EXPORTING")
        self.db.add(job)
        document.status = DocumentStatus.EXPORTING
        await self.db.flush()

        try:
            original = self.storage.resolve_original(document.original_storage_key)
            ext = self._extension_for(fmt, original)
            storage_key = f"{document_id}/{job.id}{ext}"
            dest = self.storage.export_path(storage_key)
            dest.parent.mkdir(parents=True, exist_ok=True)

            edits = await self._load_applied_edits(document)
            glyph_sources = self._glyph_sources(document)
            self.renderer.render(
                original=original,
                dest=dest,
                mime_type=document.mime_type,
                edits=edits,
                glyph_sources=glyph_sources,
            )

            job.storage_key = storage_key
            job.status = "COMPLETED"
            document.status = DocumentStatus.COMPLETED
        except Exception as exc:  # noqa: BLE001
            job.status = "FAILED"
            job.error_message = str(exc)
            document.status = DocumentStatus.EDITING if document.page_count else DocumentStatus.READY

        await self.db.commit()
        await self.db.refresh(job)
        return job

    @staticmethod
    def _glyph_sources(document: Document) -> list[GlyphSource]:
        """Collect page text lines so image export can clone real ink glyphs."""
        sources: list[GlyphSource] = []
        for page in document.pages:
            for block in page.text_blocks:
                text = (block.text or "").strip()
                if not text:
                    continue
                sources.append(
                    GlyphSource(
                        text=text,
                        bbox={
                            "x0": block.x,
                            "y0": block.y,
                            "x1": block.x + block.width,
                            "y1": block.y + block.height,
                        },
                        page_number=page.page_number,
                    )
                )
        return sources

    async def _load_applied_edits(self, document: Document) -> list[AppliedEdit]:
        result = await self.db.execute(
            select(EditOperation)
            .where(
                EditOperation.document_id == document.id,
                EditOperation.status == OperationStatus.APPLIED,
            )
            .order_by(EditOperation.created_at.asc())
        )
        operations = list(result.scalars().all())

        page_by_id = {page.id: page for page in document.pages}
        block_by_id: dict[uuid.UUID, TextBlock] = {}
        for page in document.pages:
            for block in page.text_blocks:
                block_by_id[block.id] = block

        applied: list[AppliedEdit] = []
        for op in operations:
            page = page_by_id.get(op.page_id) if op.page_id else None
            block = block_by_id.get(op.block_id) if op.block_id else None
            page_number = page.page_number if page else 1
            applied.append(
                AppliedEdit(
                    operation_type=op.operation_type.value,
                    page_number=page_number,
                    old_value=op.old_value,
                    new_value=op.new_value,
                    bbox=op.bbox,
                    font_size=(block.font_size if block else None),
                    font_family=(block.font_family if block else None),
                    block_id=str(op.block_id) if op.block_id else None,
                )
            )
        return applied

    def resolve_export_file(self, job: ExportJob) -> Path:
        if not job.storage_key:
            raise FileNotFoundError("Export has no storage key")
        path = self.storage.export_path(job.storage_key)
        if not path.exists():
            raise FileNotFoundError("Export file missing")
        return path

    async def live_page_preview(self, document_id: uuid.UUID, page_number: int) -> Path | None:
        """Raster preview with applied edits (editor left pane). Returns None if no edits."""
        result = await self.db.execute(
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.pages).selectinload(DocumentPage.text_blocks))
        )
        document = result.scalar_one_or_none()
        if document is None:
            raise LookupError("Document not found")

        edits = await self._load_applied_edits(document)
        if not edits:
            return None

        fingerprint = self._edits_fingerprint(edits)
        # Bump render_tag when preview compositing changes so stale ghost caches are skipped.
        render_tag = "r6"
        preview_key = f"{document_id}/live_p{page_number}_{render_tag}_{fingerprint}.png"
        preview_path = self.storage.working_path(preview_key)
        if preview_path.exists():
            return preview_path

        preview_path.parent.mkdir(parents=True, exist_ok=True)
        original = self.storage.resolve_original(document.original_storage_key)
        glyph_sources = self._glyph_sources(document)

        if document.mime_type == "application/pdf":
            edited_key = f"{document_id}/live_{render_tag}_{fingerprint}.pdf"
            edited_pdf = self.storage.working_path(edited_key)
            if not edited_pdf.exists():
                self.renderer.render(
                    original=original,
                    dest=edited_pdf,
                    mime_type=document.mime_type,
                    edits=edits,
                    glyph_sources=glyph_sources,
                )
            from app.services.pdf_service import PdfService

            PdfService().render_page_preview(edited_pdf, page_number, preview_path)
        else:
            self.renderer.render(
                original=original,
                dest=preview_path,
                mime_type=document.mime_type,
                edits=edits,
                glyph_sources=glyph_sources,
            )

        self._cleanup_stale_live_previews(document_id, page_number, keep=preview_path)
        return preview_path

    @staticmethod
    def _edits_fingerprint(edits: list[AppliedEdit]) -> str:
        # Stable cache key from applied edit stack (order + values).
        parts = [
            f"{e.operation_type}:{e.page_number}:{e.old_value}->{e.new_value}:{e.block_id or ''}"
            for e in edits
        ]
        digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()[:12]
        return f"{len(edits)}_{digest}"

    def _cleanup_stale_live_previews(
        self,
        document_id: uuid.UUID,
        page_number: int,
        *,
        keep: Path,
    ) -> None:
        folder = self.storage.working_path(str(document_id))
        if not folder.exists():
            return
        prefix = f"live_p{page_number}_"
        for path in folder.glob(f"{prefix}*.png"):
            if path.resolve() != keep.resolve():
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    continue

    async def get_job(self, document_id: uuid.UUID, export_id: uuid.UUID) -> ExportJob:
        result = await self.db.execute(
            select(ExportJob).where(ExportJob.id == export_id, ExportJob.document_id == document_id)
        )
        job = result.scalar_one_or_none()
        if job is None:
            raise LookupError("Export job not found")
        return job

    @staticmethod
    def _default_format(mime_type: str) -> str:
        if mime_type == "application/pdf":
            return "pdf"
        if mime_type == "image/png":
            return "png"
        return "jpg"

    @staticmethod
    def _extension_for(fmt: str, original: Path) -> str:
        if fmt == "pdf":
            return ".pdf"
        if fmt == "png":
            return ".png"
        if fmt in {"jpg", "jpeg"}:
            return ".jpg"
        return original.suffix or f".{fmt}"
