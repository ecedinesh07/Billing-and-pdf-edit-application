import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { DocumentApiService } from '../../core/api/document-api.service';
import { environment } from '../../../environments/environment';

const ACCEPTED = '.pdf,.jpg,.jpeg,.png';

@Component({
  selector: 'app-upload',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './upload.html',
  styleUrl: './upload.scss',
})
export class Upload {
  private readonly api = inject(DocumentApiService);
  private readonly router = inject(Router);

  readonly accepted = ACCEPTED;
  readonly uploading = signal(false);
  readonly progressLabel = signal('');
  readonly error = signal<string | null>(null);
  readonly dragOver = signal(false);

  onFileInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (file) {
      this.upload(file);
    }
    input.value = '';
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(false);
    const file = event.dataTransfer?.files?.[0];
    if (file) {
      this.upload(file);
    }
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.dragOver.set(true);
  }

  onDragLeave(): void {
    this.dragOver.set(false);
  }

  private describeUploadError(err: unknown): string {
    const httpErr = err as {
      status?: number;
      statusText?: string;
      error?: { detail?: string } | string;
      message?: string;
    };

    if (httpErr?.status === 0 || httpErr?.status === undefined) {
      return `Cannot reach the API at ${environment.apiBaseUrl.replace(/\/api\/v1\/?$/, '')}. Start the FastAPI backend, then try again.`;
    }

    if (typeof httpErr?.error === 'object' && httpErr.error?.detail) {
      return String(httpErr.error.detail);
    }

    if (typeof httpErr?.error === 'string' && httpErr.error.trim()) {
      return httpErr.error;
    }

    return `Upload failed (${httpErr?.status ?? 'unknown'}${httpErr?.statusText ? ' ' + httpErr.statusText : ''}). Please try again.`;
  }

  private upload(file: File): void {
    this.error.set(null);
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.jpg', '.jpeg', '.png'].includes(ext)) {
      this.error.set('Unsupported file. Please upload PDF, JPG, or PNG.');
      return;
    }

    this.uploading.set(true);
    this.progressLabel.set(`Uploading ${file.name}…`);

    this.api.upload(file).subscribe({
      next: (res) => {
        this.uploading.set(false);
        this.progressLabel.set('');
        void this.router.navigate(['/editor', res.document_id]);
      },
      error: (err) => {
        this.uploading.set(false);
        this.progressLabel.set('');
        this.error.set(this.describeUploadError(err));
      },
    });
  }
}
