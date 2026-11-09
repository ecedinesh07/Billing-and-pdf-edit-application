import { CommonModule } from '@angular/common';
import { Component, inject, signal } from '@angular/core';
import { Router } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { DocumentApiService } from '../../core/api/document-api.service';
import { ToastService } from '../../shared/toast/toast.service';

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
  private readonly toast = inject(ToastService);

  readonly accepted = ACCEPTED;
  readonly uploading = signal(false);
  readonly progressLabel = signal('');
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

  private upload(file: File): void {
    this.toast.clear();
    const ext = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    if (!['.pdf', '.jpg', '.jpeg', '.png'].includes(ext)) {
      this.toast.show('Unsupported file. Please upload PDF, JPG, or PNG.');
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
        this.toast.show(apiErrorMessage(err, 'Upload failed'));
      },
    });
  }
}
