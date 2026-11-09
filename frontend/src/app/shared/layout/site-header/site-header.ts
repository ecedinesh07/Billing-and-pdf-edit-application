import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { ThemeId, ThemeService } from '../../../core/theme/theme.service';

interface NavItem {
  label: string;
  path: string;
  exact?: boolean;
}

@Component({
  selector: 'app-site-header',
  imports: [RouterLink, RouterLinkActive],
  templateUrl: './site-header.html',
  styleUrl: './site-header.scss',
})
export class SiteHeader {
  readonly theme = inject(ThemeService);
  readonly menuOpen = signal(false);
  readonly themeOpen = signal(false);

  /** Placeholder menus for layout/testing — routes fall back to home for now. */
  readonly navItems: NavItem[] = [
    { label: 'Home', path: '/', exact: true },
    { label: 'Documents', path: '/' },
    { label: 'Templates', path: '/' },
    { label: 'Reports', path: '/' },
    { label: 'Settings', path: '/' },
    { label: 'Help', path: '/' },
  ];

  toggleMenu(): void {
    this.menuOpen.update((v) => !v);
    if (this.menuOpen()) {
      this.themeOpen.set(false);
    }
  }

  toggleThemePanel(): void {
    this.themeOpen.update((v) => !v);
    if (this.themeOpen()) {
      this.menuOpen.set(false);
    }
  }

  closeMenus(): void {
    this.menuOpen.set(false);
    this.themeOpen.set(false);
  }

  selectTheme(id: ThemeId): void {
    this.theme.setTheme(id);
    this.themeOpen.set(false);
  }
}
