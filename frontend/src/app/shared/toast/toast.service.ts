import { Injectable, signal } from '@angular/core';

export type ToastKind = 'danger';

export interface ToastMessage {
  id: number;
  text: string;
  kind: ToastKind;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
  private nextId = 0;
  private readonly timers = new Map<number, ReturnType<typeof setTimeout>>();

  readonly toasts = signal<ToastMessage[]>([]);

  show(text: string, kind: ToastKind = 'danger', durationMs = 4500): void {
    const existing = this.toasts().find((toast) => toast.text === text && toast.kind === kind);
    if (existing) {
      this.dismiss(existing.id);
    }

    const id = ++this.nextId;
    this.toasts.update((list) => [...list, { id, text, kind }]);
    if (durationMs > 0) {
      this.timers.set(
        id,
        setTimeout(() => this.dismiss(id), durationMs),
      );
    }
  }

  clear(): void {
    for (const timer of this.timers.values()) {
      clearTimeout(timer);
    }
    this.timers.clear();
    this.toasts.set([]);
  }

  dismiss(id: number): void {
    const timer = this.timers.get(id);
    if (timer !== undefined) {
      clearTimeout(timer);
      this.timers.delete(id);
    }
    this.toasts.update((list) => list.filter((toast) => toast.id !== id));
  }
}
