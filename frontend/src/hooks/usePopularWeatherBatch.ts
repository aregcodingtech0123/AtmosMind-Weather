import { useCallback, useEffect, useMemo } from 'react';
import useSWR from 'swr';

import { POPULAR_CITIES } from '../data/popularCities';
import { fetchPopularWeatherBatch, type BatchWeatherResponse } from '../services/api';
import { consumeBootPrefetch } from '../utils/popularWeatherBoot';
import {
  isPopularWeatherCacheStale,
  mapBatchToPopularWeather,
  popularWeatherStorageKey,
  readPopularWeatherCache,
  writePopularWeatherCache,
  type PopularWeatherMap,
} from '../utils/popularWeatherCache';

type PopularWeatherKey = ['popular-weather-batch', string, string];

async function fetchAndPersist(
  language: string,
  unit: string,
  options?: { forceRefresh?: boolean; useBootPrefetch?: boolean }
): Promise<PopularWeatherMap> {
  const cityNames = POPULAR_CITIES.map((c) => c.defaultName);
  // On first mount, reuse the request already started in index.tsx (see popularWeatherBoot.ts).
  // If it failed or was already consumed, fall back to a regular request.
  let batch: BatchWeatherResponse | null = null;
  const boot = options?.useBootPrefetch ? consumeBootPrefetch() : null;
  if (boot) {
    try {
      batch = await boot;
    } catch {
      batch = null;
    }
  }
  if (!batch) batch = await fetchPopularWeatherBatch(cityNames, options);
  const map = mapBatchToPopularWeather(batch);
  writePopularWeatherCache(popularWeatherStorageKey(language, unit), map);
  return map;
}

/**
 * Initial-data priority (SWR `fallbackData`); SWR then revalidates in the background:
 *   1. localStorage cache (returning visitors) — temperatures render on first paint.
 *   2. `fallbackData` argument (e.g. a static snapshot) — optional seed for first-time visitors.
 *   3. Neither: the skeleton shows only until the boot prefetch (popularWeatherBoot.ts) resolves.
 */
export function usePopularWeatherBatch(
  enabled: boolean,
  language: string,
  unit: 'metric' | 'imperial',
  fallbackData?: PopularWeatherMap
) {
  const storageKey = popularWeatherStorageKey(language, unit);
  const persisted = useMemo(
    () => (enabled ? readPopularWeatherCache(storageKey) : null),
    [enabled, storageKey]
  );

  const swrKey: PopularWeatherKey | null = enabled ? ['popular-weather-batch', language, unit] : null;

  const { data, error, isLoading, mutate } = useSWR(
    swrKey,
    () => fetchAndPersist(language, unit, { useBootPrefetch: true }),
    {
      fallbackData: persisted?.data ?? fallbackData,
      revalidateOnMount: true,
      revalidateOnFocus: false,
      dedupingInterval: 60_000,
      keepPreviousData: true,
    }
  );

  useEffect(() => {
    if (!enabled || !persisted) return;
    if (isPopularWeatherCacheStale(persisted.timestamp)) {
      void mutate();
    }
  }, [enabled, persisted, mutate]);

  const hasCachedOrFetchedData = data != null && Object.keys(data).length > 0;
  const showSkeleton = Boolean(isLoading && !hasCachedOrFetchedData);
  const hasError = Boolean(error) && !hasCachedOrFetchedData;

  const refresh = useCallback(
    (options?: { forceRefresh?: boolean }) =>
      mutate(() => fetchAndPersist(language, unit, options), { revalidate: false }),
    [language, unit, mutate]
  );

  return {
    popularCitiesWeather: data ?? {},
    popularCitiesWeatherLoading: showSkeleton,
    popularCitiesWeatherError: hasError,
    refreshPopularBatch: refresh,
  };
}
