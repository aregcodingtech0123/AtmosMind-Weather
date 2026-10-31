// Side-effect entry: imported first in index.tsx so the prefetch starts before the app boots.
// Kept separate from popularWeatherBoot.ts so importing the hook (e.g. in tests) never fires a request.
import { startBootPrefetch } from './popularWeatherBoot';

startBootPrefetch();
