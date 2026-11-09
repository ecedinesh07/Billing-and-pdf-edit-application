import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-site-footer',
  imports: [RouterLink],
  templateUrl: './site-footer.html',
  styleUrl: './site-footer.scss',
})
export class SiteFooter {
  readonly year = new Date().getFullYear();

  readonly columns = [
    {
      title: 'Product',
      links: [
        { label: 'Home', path: '/' },
        { label: 'Documents', path: '/' },
        { label: 'Templates', path: '/' },
      ],
    },
    {
      title: 'Workspace',
      links: [
        { label: 'Reports', path: '/' },
        { label: 'Settings', path: '/' },
        { label: 'Help Center', path: '/' },
      ],
    },
    {
      title: 'Company',
      links: [
        { label: 'About EasyDoc', path: '/' },
        { label: 'Privacy', path: '/' },
        { label: 'Terms', path: '/' },
      ],
    },
  ];
}
