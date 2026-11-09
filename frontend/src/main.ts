import { bootstrapApplication } from '@angular/platform-browser';

import { appConfig } from './app/app.config';
import { App } from './app/app';
import './app/core/firebase/firebase-app';

bootstrapApplication(App, appConfig)
  .catch((err) => console.error(err));
