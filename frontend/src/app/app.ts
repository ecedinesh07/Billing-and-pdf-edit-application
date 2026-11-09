import { Component, signal } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';

import { ToastHost } from './shared/toast/toast-host';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, ToastHost],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  protected readonly title = signal('Document Text Correction');
}
