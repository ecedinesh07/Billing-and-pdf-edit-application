import { Component, inject } from '@angular/core';

import { ToastService } from './toast.service';

@Component({
  selector: 'app-toast-host',
  templateUrl: './toast-host.html',
  styleUrl: './toast-host.scss',
})
export class ToastHost {
  private readonly toast = inject(ToastService);

  readonly toasts = this.toast.toasts;

  dismiss(id: number): void {
    this.toast.dismiss(id);
  }
}
