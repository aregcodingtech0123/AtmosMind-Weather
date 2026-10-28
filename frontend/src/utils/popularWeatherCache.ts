import { POPULAR_CITIES } from '../data/popularCities';
import type { BatchWeatherResponse } from '../services/api';
import type { ResponseMeta } from '../types/resilience';

export const POPULAR_WEATHER_CACHE_PREFIX = 'atmosmind_popular_weather_cache_';

/** Soft TTL: show cached data instantly; revalidate in background after this age. */
export const POPULAR_WEATHER_CACHE_TTL_MS = 15 * 60 * 1000;

export interface PopularCityWeather {
  temperature: number | null;
  condition: string | null;
  weather_code: number | null;
  meta?: ResponseMeta | null;
}

export type PopularWeatherMap = Record<string, PopularCityWeather>;

interface PersistedPopularWeather {
  data: PopularWeatherMap;
  timestamp: number;
}

export function popularCacheHasMeta(data: PopularWeatherMap): boolean {
  const values = Object.values(data);
  if (values.length === 0) return false;
  return values.some((entry) => entry.meta != null && typeof entry.meta.data_status === 'string');
}

export function popularWeatherStorageKey(language: string, unit: string): string {
  return `${POPULAR_WEATHER_CACHE_PREFIX}${language}_${unit}`;
}

export function readPopularWeatherCache(storageKey: string): PersistedPopularWeather | null {
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as PersistedPopularWeather;
    if (!parsed?.data || typeof parsed.timestamp !== 'number') return null;
    if (!popularCacheHasMeta(parsed.data)) return null;
    return parsed;
  } catch {
    return null;
  }
}

export function writePopularWeatherCache(storageKey: string, data: PopularWeatherMap): void {
  if (!popularCacheHasMeta(data)) return;
  localStorage.setItem(
    storageKey,
    JSON.stringify({
      data,
      timestamp: Date.now(),
    } satisfies PersistedPopularWeather)
  );
}

export function mapBatchToPopularWeather(batch: BatchWeatherResponse): PopularWeatherMap {
  const map: PopularWeatherMap = {};
  POPULAR_CITIES.forEach((city) => {
    const item =
      batch.results.find((result) => result.city === city.defaultName) ??
      batch.results.find((result) => result.city.startsWith(city.names.en));
    if (!item) return;
    map[city.id] = {
      temperature: item.temperature,
      condition: item.condition,
      weather_code: item.weather_code,
      meta: item.meta ?? null,
    };
  });
  return map;
}

export function isPopularWeatherCacheStale(timestamp: number, ttlMs = POPULAR_WEATHER_CACHE_TTL_MS): boolean {
  return Date.now() - timestamp >= ttlMs;
}
