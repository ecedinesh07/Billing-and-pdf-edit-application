from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UploadResponse(BaseModel):
    document_id: UUID
    status: str
    original_filename: str
    mime_type: str
    message: str = "Upload accepted"


class DocumentStatusResponse(BaseModel):
    document_id: UUID
    status: str
    page_count: int
    source_type: str
    error_message: str | None = None


class TextBlockSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: str = "text"
    text: str
    bbox: list[float] = Field(description="[x0, y0, x1, y1]")
    language: str | None = None
    direction: str = "ltr"
    confidence: float | None = None
    font_family: str | None = None
    font_size: float | None = None
    rotation: float = 0.0


class PageSchema(BaseModel):
    page_number: int
    width: float
    height: float
    rotation: float = 0.0
    blocks: list[TextBlockSchema] = []


class NormalizedDocument(BaseModel):
    document_id: UUID
    source_type: str
    status: str
    pages: list[PageSchema] = []


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_filename: str
    source_type: str
    mime_type: str
    page_count: int
    status: str
    created_at: datetime
    updated_at: datetime


class EditOperationCreate(BaseModel):
    type: str = Field(description="replace_text | insert_text | delete_text | …")
    page: int
    block_id: UUID | None = None
    old_text: str | None = None
    new_text: str | None = None
    bbox: list[float] | None = None


class EditOperationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    operation_type: str
    old_value: str | None
    new_value: str | None
    bbox: dict | list | None = None
    status: str
    created_at: datetime
