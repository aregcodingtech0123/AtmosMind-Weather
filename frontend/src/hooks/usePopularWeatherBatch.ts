import { useCallback, useEffect, useMemo } from 'react';
import useSWR from 'swr';

import { POPULAR_CITIES } from '../data/popularCities';
import { fetchPopularWeatherBatch } from '../services/api';
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
  options?: { forceRefresh?: boolean }
): Promise<PopularWeatherMap> {
  const cityNames = POPULAR_CITIES.map((c) => c.defaultName);
  const batch = await fetchPopularWeatherBatch(cityNames, options);
  const map = mapBatchToPopularWeather(batch);
  writePopularWeatherCache(popularWeatherStorageKey(language, unit), map);
  return map;
}

export function usePopularWeatherBatch(
  enabled: boolean,
  language: string,
  unit: 'metric' | 'imperial'
) {
  const storageKey = popularWeatherStorageKey(language, unit);
  const persisted = useMemo(
    () => (enabled ? readPopularWeatherCache(storageKey) : null),
    [enabled, storageKey]
  );

  const swrKey: PopularWeatherKey | null = enabled ? ['popular-weather-batch', language, unit] : null;

  const { data, error, isLoading, mutate } = useSWR(
    swrKey,
    () => fetchAndPersist(language, unit),
    {
      fallbackData: persisted?.data,
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
