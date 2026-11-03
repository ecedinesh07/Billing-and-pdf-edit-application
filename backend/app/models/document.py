import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SourceType(str, enum.Enum):
    TEXT_PDF = "text_pdf"
    SCANNED_PDF = "scanned_pdf"
    IMAGE = "image"
    UNKNOWN = "unknown"


class DocumentStatus(str, enum.Enum):
    UPLOADING = "UPLOADING"
    PROCESSING = "PROCESSING"
    OCR_RUNNING = "OCR_RUNNING"
    READY = "READY"
    EDITING = "EDITING"
    EXPORTING = "EXPORTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class OperationType(str, enum.Enum):
    REPLACE_TEXT = "replace_text"
    INSERT_TEXT = "insert_text"
    DELETE_TEXT = "delete_text"
    MOVE_TEXT = "move_text"
    RESIZE_TEXT = "resize_text"
    ROTATE_TEXT = "rotate_text"


class OperationStatus(str, enum.Enum):
    PENDING = "pending"
    APPLIED = "applied"
    UNDONE = "undone"
    REJECTED = "rejected"


def _enum(enum_cls: type[enum.Enum], name: str) -> Enum:
    # native_enum=False keeps SQLite and PostgreSQL compatible
    return Enum(enum_cls, name=name, native_enum=False, values_callable=lambda e: [m.value for m in e])


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid(as_uuid=True), nullable=True, index=True)
    original_filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        _enum(SourceType, "source_type"), default=SourceType.UNKNOWN, nullable=False
    )
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    original_storage_key: Mapped[str] = mapped_column(String(1024), nullable=False)
    status: Mapped[DocumentStatus] = mapped_column(
        _enum(DocumentStatus, "document_status"),
        default=DocumentStatus.UPLOADING,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    pages: Mapped[list["DocumentPage"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    edit_operations: Mapped[list["EditOperation"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    exports: Mapped[list["ExportJob"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class DocumentPage(Base):
    __tablename__ = "document_pages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    preview_storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    rotation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    document: Mapped["Document"] = relationship(back_populates="pages")
    text_blocks: Mapped[list["TextBlock"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )


class TextBlock(Base):
    __tablename__ = "text_blocks"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    x: Mapped[float] = mapped_column(Float, nullable=False)
    y: Mapped[float] = mapped_column(Float, nullable=False)
    width: Mapped[float] = mapped_column(Float, nullable=False)
    height: Mapped[float] = mapped_column(Float, nullable=False)
    font_family: Mapped[str | None] = mapped_column(String(256), nullable=True)
    font_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    font_weight: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rotation: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    direction: Mapped[str] = mapped_column(String(8), default="ltr", nullable=False)
    ocr_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    page: Mapped["DocumentPage"] = relationship(back_populates="text_blocks")


class EditOperation(Base):
    __tablename__ = "edit_operations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("document_pages.id", ondelete="SET NULL"), nullable=True
    )
    block_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("text_blocks.id", ondelete="SET NULL"), nullable=True
    )
    operation_type: Mapped[OperationType] = mapped_column(_enum(OperationType, "operation_type"), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    new_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    bbox: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    status: Mapped[OperationStatus] = mapped_column(
        _enum(OperationStatus, "operation_status"),
        default=OperationStatus.APPLIED,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="edit_operations")


class ExportJob(Base):
    __tablename__ = "exports"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    output_format: Mapped[str] = mapped_column(String(32), nullable=False)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    document: Mapped["Document"] = relationship(back_populates="exports")
