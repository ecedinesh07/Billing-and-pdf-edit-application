import { Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { ThemeService } from './core/theme/theme.service';
import { SiteFooter } from './shared/layout/site-footer/site-footer';
import { SiteHeader } from './shared/layout/site-header/site-header';

import { ToastHost } from './shared/toast/toast-host';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, SiteHeader, ToastHost, SiteFooter],
  templateUrl: './app.html',
  styleUrl: './app.scss',
})
export class App {
  /** Eagerly apply persisted theme before first paint of child routes. */
  private readonly theme = inject(ThemeService);
}
