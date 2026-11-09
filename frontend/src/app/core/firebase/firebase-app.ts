import { getAnalytics, isSupported } from 'firebase/analytics';
import { initializeApp } from 'firebase/app';

import { environment } from '../../../environments/environment';

export const firebaseApp = initializeApp(environment.firebase);

void isSupported().then((supported) => {
  if (supported) {
    getAnalytics(firebaseApp);
  }
});
