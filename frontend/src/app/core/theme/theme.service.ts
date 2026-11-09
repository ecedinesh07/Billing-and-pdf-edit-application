import { Injectable, signal, computed, effect } from '@angular/core';

export type ThemeId =
  | 'aqua'
  | 'black'
  | 'meadow'
  | 'sunset'
  | 'ocean'
  | 'berry'
  | 'citrus'
  | 'midnight';

export interface ThemeDefinition {
  id: ThemeId;
  label: string;
  swatch: string;
  vars: Record<string, string>;
}

const STORAGE_KEY = 'dtc-theme';
const DEFAULT_THEME: ThemeId = 'aqua';

export const THEMES: ThemeDefinition[] = [
  {
    id: 'aqua',
    label: 'Aqua',
    swatch: 'linear-gradient(135deg, #067a86, #14c4d4)',
    vars: {
      '--ink': '#e6f7f9',
      '--muted': '#8eb8bf',
      '--line': '#1f4f57',
      '--surface': '#0b2c32',
      '--surface-elevated': '#123940',
      '--accent': '#1ad0df',
      '--accent-strong': '#0ea5b3',
      '--accent-soft': '#164850',
      '--accent-contrast': '#042328',
      '--secondary': '#ff8a65',
      '--danger': '#fb7185',
      '--header-bg': 'linear-gradient(120deg, #06262c 0%, #0c343b 45%, #11454e 100%)',
      '--header-border': '#1f5560',
      '--footer-bg': 'linear-gradient(165deg, #02161a 0%, #041f24 48%, #0a3038 100%)',
      '--footer-ink': '#e6f7f9',
      '--footer-muted': '#7faab2',
      '--glow-a': '#0a3d46',
      '--glow-b': '#083038',
      '--page-top': '#061f24',
      '--page-mid': '#08272d',
      '--page-end': '#04181c',
      '--nav-active': '#1ad0df',
      '--chip-ring': '#14c4d4',
    },
  },
  {
    id: 'black',
    label: 'Black',
    swatch: 'linear-gradient(135deg, #000000, #3f3f46)',
    vars: {
      '--ink': '#f4f4f5',
      '--muted': '#a1a1aa',
      '--line': '#2a2a2e',
      '--surface': '#0a0a0b',
      '--surface-elevated': '#161618',
      '--accent': '#f4f4f5',
      '--accent-strong': '#ffffff',
      '--accent-soft': '#27272a',
      '--accent-contrast': '#09090b',
      '--secondary': '#22d3ee',
      '--danger': '#fb7185',
      '--header-bg': 'linear-gradient(120deg, #000000 0%, #121214 50%, #1a1a1d 100%)',
      '--header-border': '#2f2f33',
      '--footer-bg': 'linear-gradient(165deg, #000000 0%, #050505 45%, #101012 100%)',
      '--footer-ink': '#f4f4f5',
      '--footer-muted': '#a1a1aa',
      '--glow-a': '#1f2937',
      '--glow-b': '#111827',
      '--page-top': '#050505',
      '--page-mid': '#0a0a0b',
      '--page-end': '#000000',
      '--nav-active': '#22d3ee',
      '--chip-ring': '#52525b',
    },
  },
  {
    id: 'meadow',
    label: 'Meadow',
    swatch: 'linear-gradient(135deg, #2f6b4f, #8fbf7a)',
    vars: {
      '--ink': '#1c241c',
      '--muted': '#5d675d',
      '--line': '#c5d6c8',
      '--surface': '#f3f6f2',
      '--surface-elevated': '#ffffff',
      '--accent': '#2f6b4f',
      '--accent-strong': '#1f4d38',
      '--accent-soft': '#d8eedf',
      '--accent-contrast': '#ffffff',
      '--secondary': '#c4783a',
      '--danger': '#a13a2d',
      '--header-bg': 'linear-gradient(120deg, #e7f5ea 0%, #fffef8 48%, #f0ebe0 100%)',
      '--header-border': '#b7d0bc',
      '--footer-bg': 'linear-gradient(160deg, #163528 0%, #1c241c 42%, #2a1f14 100%)',
      '--footer-ink': '#e8efe6',
      '--footer-muted': '#a7b5a8',
      '--glow-a': '#e7efe6',
      '--glow-b': '#e8e2d6',
      '--page-top': '#f7f8f5',
      '--page-mid': '#eef1ec',
      '--page-end': '#e8ebe4',
      '--nav-active': '#2f6b4f',
      '--chip-ring': '#8fbf7a',
    },
  },
  {
    id: 'sunset',
    label: 'Sunset',
    swatch: 'linear-gradient(135deg, #c2410c, #f59e0b)',
    vars: {
      '--ink': '#2a1810',
      '--muted': '#7a5648',
      '--line': '#efc9b0',
      '--surface': '#fff7f1',
      '--surface-elevated': '#ffffff',
      '--accent': '#c2410c',
      '--accent-strong': '#9a3412',
      '--accent-soft': '#ffedd5',
      '--accent-contrast': '#ffffff',
      '--secondary': '#0ea5a4',
      '--danger': '#b91c1c',
      '--header-bg': 'linear-gradient(115deg, #ffe8d4 0%, #fff8ef 45%, #ffd9a8 100%)',
      '--header-border': '#efb78a',
      '--footer-bg': 'linear-gradient(165deg, #3b1508 0%, #2a1810 50%, #12353a 100%)',
      '--footer-ink': '#fff4ec',
      '--footer-muted': '#d4b4a4',
      '--glow-a': '#ffe4d1',
      '--glow-b': '#fde68a',
      '--page-top': '#fffaf6',
      '--page-mid': '#fff1e6',
      '--page-end': '#f8e6d8',
      '--nav-active': '#c2410c',
      '--chip-ring': '#f59e0b',
    },
  },
  {
    id: 'ocean',
    label: 'Ocean',
    swatch: 'linear-gradient(135deg, #0e7490, #38bdf8)',
    vars: {
      '--ink': '#0b2530',
      '--muted': '#4d6b76',
      '--line': '#a9cede',
      '--surface': '#f0f9fc',
      '--surface-elevated': '#ffffff',
      '--accent': '#0e7490',
      '--accent-strong': '#155e75',
      '--accent-soft': '#cffafe',
      '--accent-contrast': '#ffffff',
      '--secondary': '#f97316',
      '--danger': '#be123c',
      '--header-bg': 'linear-gradient(120deg, #d7f3fb 0%, #f4fbfe 42%, #dff0ff 100%)',
      '--header-border': '#8ec8dc',
      '--footer-bg': 'linear-gradient(165deg, #062433 0%, #0b2530 48%, #1a3348 100%)',
      '--footer-ink': '#e8f7fb',
      '--footer-muted': '#9cbcc8',
      '--glow-a': '#d9f3fa',
      '--glow-b': '#e0f2fe',
      '--page-top': '#f7fcfe',
      '--page-mid': '#eaf6fb',
      '--page-end': '#dceef5',
      '--nav-active': '#0e7490',
      '--chip-ring': '#38bdf8',
    },
  },
  {
    id: 'berry',
    label: 'Berry',
    swatch: 'linear-gradient(135deg, #9d174d, #fb7185)',
    vars: {
      '--ink': '#2a0f1c',
      '--muted': '#7a4d61',
      '--line': '#e5b4c7',
      '--surface': '#fff5f8',
      '--surface-elevated': '#ffffff',
      '--accent': '#9d174d',
      '--accent-strong': '#831843',
      '--accent-soft': '#fce7f3',
      '--accent-contrast': '#ffffff',
      '--secondary': '#059669',
      '--danger': '#b91c1c',
      '--header-bg': 'linear-gradient(120deg, #ffe0ec 0%, #fff7fa 46%, #ffe8f2 100%)',
      '--header-border': '#e8a5bd',
      '--footer-bg': 'linear-gradient(165deg, #3a0f24 0%, #2a0f1c 45%, #123528 100%)',
      '--footer-ink': '#ffeef5',
      '--footer-muted': '#d9a8bc',
      '--glow-a': '#fce7f3',
      '--glow-b': '#fde68a',
      '--page-top': '#fffafb',
      '--page-mid': '#fff1f5',
      '--page-end': '#f8e4ec',
      '--nav-active': '#9d174d',
      '--chip-ring': '#fb7185',
    },
  },
  {
    id: 'citrus',
    label: 'Citrus',
    swatch: 'linear-gradient(135deg, #65a30d, #facc15)',
    vars: {
      '--ink': '#1a220c',
      '--muted': '#617044',
      '--line': '#c7d89a',
      '--surface': '#f8fce9',
      '--surface-elevated': '#ffffff',
      '--accent': '#65a30d',
      '--accent-strong': '#4d7c0f',
      '--accent-soft': '#ecfccb',
      '--accent-contrast': '#14200a',
      '--secondary': '#ea580c',
      '--danger': '#b91c1c',
      '--header-bg': 'linear-gradient(120deg, #eaf8c4 0%, #fcfef3 44%, #fff3bf 100%)',
      '--header-border': '#c3d97a',
      '--footer-bg': 'linear-gradient(165deg, #1f2c0c 0%, #1a220c 50%, #3b1d08 100%)',
      '--footer-ink': '#f4fadb',
      '--footer-muted': '#b4c48a',
      '--glow-a': '#ecfccb',
      '--glow-b': '#fef08a',
      '--page-top': '#fcfef4',
      '--page-mid': '#f3f9df',
      '--page-end': '#e7f0c8',
      '--nav-active': '#65a30d',
      '--chip-ring': '#facc15',
    },
  },
  {
    id: 'midnight',
    label: 'Midnight',
    swatch: 'linear-gradient(135deg, #1e293b, #38bdf8)',
    vars: {
      '--ink': '#e8eef7',
      '--muted': '#9aa8bc',
      '--line': '#3d4f66',
      '--surface': '#1e293b',
      '--surface-elevated': '#273449',
      '--accent': '#38bdf8',
      '--accent-strong': '#0ea5e9',
      '--accent-soft': '#0c4a6e',
      '--accent-contrast': '#0b1220',
      '--secondary': '#fbbf24',
      '--danger': '#fb7185',
      '--header-bg': 'linear-gradient(120deg, #152238 0%, #1e293b 48%, #243b55 100%)',
      '--header-border': '#3d5573',
      '--footer-bg': 'linear-gradient(165deg, #020617 0%, #0b1220 45%, #111827 100%)',
      '--footer-ink': '#e2e8f0',
      '--footer-muted': '#94a3b8',
      '--glow-a': '#0c4a6e',
      '--glow-b': '#1e1b4b',
      '--page-top': '#0f172a',
      '--page-mid': '#111827',
      '--page-end': '#0b1220',
      '--nav-active': '#38bdf8',
      '--chip-ring': '#38bdf8',
    },
  },
];

@Injectable({ providedIn: 'root' })
export class ThemeService {
  readonly themes = THEMES;
  readonly themeId = signal<ThemeId>(this.readStored());
  readonly activeTheme = computed(
    () => THEMES.find((t) => t.id === this.themeId()) ?? THEMES[0],
  );

  constructor() {
    effect(() => {
      const theme = this.activeTheme();
      this.apply(theme);
      try {
        localStorage.setItem(STORAGE_KEY, theme.id);
      } catch {
        /* ignore */
      }
    });
  }

  setTheme(id: ThemeId): void {
    if (THEMES.some((t) => t.id === id)) {
      this.themeId.set(id);
    }
  }

  private readStored(): ThemeId {
    try {
      const raw = localStorage.getItem(STORAGE_KEY) as ThemeId | null;
      if (raw && THEMES.some((t) => t.id === raw)) {
        return raw;
      }
    } catch {
      /* ignore */
    }
    return DEFAULT_THEME;
  }

  private apply(theme: ThemeDefinition): void {
    const root = document.documentElement;
    root.dataset['theme'] = theme.id;
    for (const [key, value] of Object.entries(theme.vars)) {
      root.style.setProperty(key, value);
    }
    root.style.colorScheme =
      theme.id === 'midnight' || theme.id === 'black' || theme.id === 'aqua' ? 'dark' : 'light';
  }
}
