/**
 * Boot-time prefetch for the homepage popular-city batch.
 *
 * Data flow for a first-time visitor (no localStorage cache):
 *   1. index.tsx imports `startPopularWeatherBoot` FIRST (it calls startBootPrefetch()), so `POST /api/weather/batch` starts as soon as the
 *      bundle executes — before i18n init, providers, routing and App's first render.
 *   2. React mounts; `usePopularWeatherBatch` runs its SWR fetcher, which calls
 *      `consumeBootPrefetch()` and awaits this already in-flight request instead of starting a
 *      second one (the request overlaps with React boot rather than following it).
 *   3. The result is mapped and persisted by the hook, so later visits use the localStorage cache.
 *
 * The request body is only the city list (independent of language/unit), so one prefetch is valid
 * for whatever language/unit the settings resolve to. Single-use: consumed once, then cleared.
 */
import { POPULAR_CITIES } from '../data/popularCities';
import { fetchPopularWeatherBatch, type BatchWeatherResponse } from '../services/api';

let pending: Promise<BatchWeatherResponse> | null = null;

function isHomePath(): boolean {
  const { pathname } = window.location;
  return pathname === '/' || pathname === '';
}

export function startBootPrefetch(): void {
  if (pending || typeof window === 'undefined' || !isHomePath()) return;
  pending = fetchPopularWeatherBatch(POPULAR_CITIES.map((c) => c.defaultName));
  // Avoid an unhandled-rejection warning if nothing consumes it; the consumer handles errors.
  pending.catch(() => undefined);
}

/** Returns the in-flight boot request once, or null (callers then fetch normally). */
export function consumeBootPrefetch(): Promise<BatchWeatherResponse> | null {
  const p = pending;
  pending = null;
  return p;
}

