import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  DocumentMeta,
  DocumentStatusResponse,
  EditOperation,
  EditOperationCreate,
  NormalizedDocument,
  UploadResponse,
} from '../../shared/models/document.model';

@Injectable({ providedIn: 'root' })
export class DocumentApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiBaseUrl;

  upload(file: File): Observable<UploadResponse> {
    const form = new FormData();
    form.append('file', file, file.name);
    return this.http.post<UploadResponse>(`${this.base}/uploads`, form);
  }

  getDocument(documentId: string): Observable<DocumentMeta> {
    return this.http.get<DocumentMeta>(`${this.base}/documents/${documentId}`);
  }

  getStatus(documentId: string): Observable<DocumentStatusResponse> {
    return this.http.get<DocumentStatusResponse>(`${this.base}/documents/${documentId}/status`);
  }

  getModel(documentId: string): Observable<NormalizedDocument> {
    return this.http.get<NormalizedDocument>(`${this.base}/documents/${documentId}/model`);
  }

  createEdit(documentId: string, payload: EditOperationCreate): Observable<EditOperation> {
    return this.http.post<EditOperation>(`${this.base}/documents/${documentId}/edits`, payload);
  }

  listEdits(documentId: string): Observable<EditOperation[]> {
    return this.http.get<EditOperation[]>(`${this.base}/documents/${documentId}/edits`);
  }

  undo(documentId: string): Observable<EditOperation> {
    return this.http.post<EditOperation>(`${this.base}/documents/${documentId}/edits/undo`, {});
  }

  redo(documentId: string): Observable<EditOperation> {
    return this.http.post<EditOperation>(`${this.base}/documents/${documentId}/edits/redo`, {});
  }

  export(documentId: string, outputFormat?: string): Observable<{ export_id: string; status: string }> {
    const params = outputFormat ? `?output_format=${encodeURIComponent(outputFormat)}` : '';
    return this.http.post<{ export_id: string; status: string }>(
      `${this.base}/documents/${documentId}/exports${params}`,
      {}
    );
  }

  downloadUrl(documentId: string, exportId: string): string {
    return `${this.base}/documents/${documentId}/exports/${exportId}/download`;
  }

  pagePreviewUrl(documentId: string, pageNumber: number, cacheBust?: string | number): string {
    const base = `${this.base}/documents/${documentId}/pages/${pageNumber}/preview`;
    return cacheBust === undefined || cacheBust === null || cacheBust === ''
      ? base
      : `${base}?v=${encodeURIComponent(String(cacheBust))}`;
  }
}
