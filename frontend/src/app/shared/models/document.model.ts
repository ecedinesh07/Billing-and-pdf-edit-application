export type DocumentStatus =
  | 'UPLOADING'
  | 'PROCESSING'
  | 'OCR_RUNNING'
  | 'READY'
  | 'EDITING'
  | 'EXPORTING'
  | 'COMPLETED'
  | 'FAILED';

export type SourceType = 'text_pdf' | 'scanned_pdf' | 'image' | 'unknown';

export interface UploadResponse {
  document_id: string;
  status: DocumentStatus;
  original_filename: string;
  mime_type: string;
  message: string;
}

export interface DocumentMeta {
  id: string;
  original_filename: string;
  source_type: SourceType;
  mime_type: string;
  page_count: number;
  status: DocumentStatus;
  created_at: string;
  updated_at: string;
}

export interface DocumentStatusResponse {
  document_id: string;
  status: DocumentStatus;
  page_count: number;
  source_type: SourceType;
  error_message?: string | null;
}

export interface TextBlock {
  id: string;
  type: 'text';
  text: string;
  bbox: [number, number, number, number];
  language?: string | null;
  direction: string;
  confidence?: number | null;
  font_family?: string | null;
  font_size?: number | null;
  rotation: number;
}

export interface DocumentPage {
  page_number: number;
  width: number;
  height: number;
  rotation: number;
  blocks: TextBlock[];
}

export interface NormalizedDocument {
  document_id: string;
  source_type: SourceType;
  status: DocumentStatus;
  pages: DocumentPage[];
}

export interface EditOperationCreate {
  type: 'replace_text' | 'insert_text' | 'delete_text' | string;
  page: number;
  block_id?: string | null;
  old_text?: string | null;
  new_text?: string | null;
  bbox?: [number, number, number, number] | null;
}

export interface EditOperation {
  id: string;
  document_id: string;
  operation_type: string;
  old_value?: string | null;
  new_value?: string | null;
  bbox?: Record<string, number> | null;
  status: string;
  created_at: string;
}
