import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    loadComponent: () => import('./features/upload/upload').then((m) => m.Upload),
  },
  {
    path: 'editor/:documentId',
    loadComponent: () =>
      import('./features/document-editor/document-editor').then((m) => m.DocumentEditor),
  },
  { path: '**', redirectTo: '' },
];
