import { CommonModule } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';

import { apiErrorMessage } from '../../core/api/api-error';
import { DocumentApiService } from '../../core/api/document-api.service';
import {
  DocumentMeta,
  EditOperation,
  NormalizedDocument,
  TextBlock,
} from '../../shared/models/document.model';
import { ToastService } from '../../shared/toast/toast.service';

@Component({
  selector: 'app-document-editor',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterLink],
  templateUrl: './document-editor.html',
  styleUrl: './document-editor.scss',
})
export class DocumentEditor implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(DocumentApiService);
  private readonly toast = inject(ToastService);

  readonly loading = signal(true);
  readonly meta = signal<DocumentMeta | null>(null);
  readonly model = signal<NormalizedDocument | null>(null);
  readonly selected = signal<TextBlock | null>(null);
  readonly editText = signal('');
  readonly operations = signal<EditOperation[]>([]);
  readonly busy = signal(false);
  readonly pageIndex = signal(0);
  /** Bumps after apply/undo/redo so the left preview reloads edited pixels. */
  readonly previewRevision = signal(0);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('documentId');
    if (!id) {
      this.toast.show('Missing document id', 'danger', 0);
      this.loading.set(false);
      return;
    }
    this.load(id);
  }

  get documentId(): string {
    return this.route.snapshot.paramMap.get('documentId') ?? '';
  }

  currentPage() {
    const pages = this.model()?.pages ?? [];
    return pages[this.pageIndex()] ?? null;
  }

  previewUrl(): string | null {
    const page = this.currentPage();
    if (!page || !this.documentId) {
      return null;
    }
    const applied = this.operations()
      .filter((op) => op.status === 'applied')
      .map((op) => op.id)
      .join('.');
    const bust = `${this.previewRevision()}-${applied || 'base'}`;
    return this.api.pagePreviewUrl(this.documentId, page.page_number, bust);
  }

  selectBlock(block: TextBlock): void {
    this.selected.set(block);
    this.editText.set(block.text);
  }

  applyReplace(): void {
    const block = this.selected();
    const page = this.currentPage();
    if (!block || !page) {
      return;
    }
    const newText = this.editText();
    if (newText === block.text) {
      this.toast.show('Replacement text is unchanged');
      return;
    }

    this.busy.set(true);
    this.api
      .createEdit(this.documentId, {
        type: 'replace_text',
        page: page.page_number,
        block_id: block.id,
        old_text: block.text,
        new_text: newText,
        bbox: block.bbox,
      })
      .subscribe({
        next: () => {
          this.previewRevision.update((n) => n + 1);
          this.reloadModel();
          this.busy.set(false);
        },
        error: (err) => {
          this.showApiError(err, 'Edit failed');
          this.busy.set(false);
        },
      });
  }

  undo(): void {
    this.busy.set(true);
    this.api.undo(this.documentId).subscribe({
      next: () => {
        this.previewRevision.update((n) => n + 1);
        this.reloadModel();
        this.busy.set(false);
      },
      error: (err) => {
        this.showApiError(err, 'Undo failed');
        this.busy.set(false);
      },
    });
  }

  redo(): void {
    this.busy.set(true);
    this.api.redo(this.documentId).subscribe({
      next: () => {
        this.previewRevision.update((n) => n + 1);
        this.reloadModel();
        this.busy.set(false);
      },
      error: (err) => {
        this.showApiError(err, 'Redo failed');
        this.busy.set(false);
      },
    });
  }

  exportDocument(): void {
    this.busy.set(true);
    this.api.export(this.documentId).subscribe({
      next: (res) => {
        this.busy.set(false);
        window.open(this.api.downloadUrl(this.documentId, res.export_id), '_blank');
      },
      error: (err) => {
        this.showApiError(err, 'Export failed');
        this.busy.set(false);
      },
    });
  }

  prevPage(): void {
    this.pageIndex.update((i) => Math.max(0, i - 1));
    this.selected.set(null);
  }

  nextPage(): void {
    const max = (this.model()?.pages.length ?? 1) - 1;
    this.pageIndex.update((i) => Math.min(max, i + 1));
    this.selected.set(null);
  }

  private showApiError(err: unknown, fallback: string, sticky = false): void {
    this.toast.show(apiErrorMessage(err, fallback), 'danger', sticky ? 0 : 6000);
  }

  private load(id: string): void {
    this.toast.clear();
    this.loading.set(true);
    this.api.getDocument(id).subscribe({
      next: (meta) => {
        this.meta.set(meta);
        this.reloadModel();
      },
      error: (err) => {
        this.showApiError(err, 'Failed to load document', true);
        this.loading.set(false);
      },
    });
  }

  private reloadModel(): void {
    this.api.getModel(this.documentId).subscribe({
      next: (model) => {
        this.model.set(model);
        this.loading.set(false);
        const sel = this.selected();
        if (sel) {
          const page = model.pages.find((p) => p.blocks.some((b) => b.id === sel.id));
          const updated = page?.blocks.find((b) => b.id === sel.id) ?? null;
          this.selected.set(updated);
          if (updated) {
            this.editText.set(updated.text);
          }
        }
      },
      error: (err) => {
        this.showApiError(err, 'Failed to load document model', true);
        this.loading.set(false);
      },
    });

    this.api.listEdits(this.documentId).subscribe({
      next: (ops) => this.operations.set(ops),
      error: (err) => this.showApiError(err, 'Failed to load edit history'),
    });
  }
}
