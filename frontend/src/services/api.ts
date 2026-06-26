/**
 * Backend origin from `REACT_APP_API_URL` (no trailing slash).
 * Use the API **host only** (e.g. https://api.example.com), not .../api — paths already include /api/...
 * If the env value ends with /api, it is stripped so we never double-prefix (/api/api/...).
 */
import type { LifestyleIndices } from '../types/weather';
import type { WeatherDetailApiResponse } from '../utils/weatherDetailMapper';

function normalizeApiBase(raw: string | undefined): string {
  if (raw == null || !String(raw).trim()) return '';
  let base = String(raw).trim().replace(/\/+$/, '');
  if (base.endsWith('/api')) {
    base = base.slice(0, -4);
  }
  return base.replace(/\/+$/, '');
}

export const API_BASE = normalizeApiBase(process.env.REACT_APP_API_URL) || '';

if (process.env.NODE_ENV === 'production' && !API_BASE) {
  // eslint-disable-next-line no-console
  console.error(
    'AtmosMind: REACT_APP_API_URL is not set. Configure it in your host (e.g. Vercel Environment Variables).'
  );
}

/** Absolute or same-origin path for API requests. */
export function apiUrl(path: string): string {
  const p = path.startsWith('/') ? path : `/${path}`;
  return API_BASE ? `${API_BASE}${p}` : p;
}

type JsonHeaders = Record<string, string>;

const JSON_HEADERS: JsonHeaders = {
  'Content-Type': 'application/json',
  'Accept-Charset': 'utf-8',
};

async function postJson<TResponse, TBody>(url: string, body: TBody): Promise<TResponse> {
  const response = await fetch(url, {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<TResponse>;
}

export interface GeoSearchResult {
  name?: string;
  country?: string;
  country_code?: string;
  admin1?: string;
  feature_code?: string;
  population?: number;
  latitude: number;
  longitude: number;
}

export async function geocodeCity(
  name: string,
  language: string,
  count = 1,
  options?: { signal?: AbortSignal }
): Promise<GeoSearchResult[]> {
  const response = await fetch(
    `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(
      name
    )}&count=${count}&language=${encodeURIComponent(language)}&format=json`,
    { headers: { 'Accept-Charset': 'utf-8' }, signal: options?.signal }
  );
  if (!response.ok) return [];
  const data = (await response.json()) as { results?: GeoSearchResult[] };
  return data.results ?? [];
}

/**
 * Reverse geocode coordinates to get city/locality name.
 *
 * Strategy:
 *   1. Nominatim (OpenStreetMap) — free, no API key, reliable, supports localization
 *   2. BigDataCloud — free fallback, no API key
 *   3. Returns null so callers can use their fallback name
 */
export async function reverseGeocode(
  latitude: number,
  longitude: number,
  language: string
): Promise<GeoSearchResult | null> {
  // Strategy 1: Nominatim (OpenStreetMap) reverse geocoding
  try {
    const nominatimUrl = `https://nominatim.openstreetmap.org/reverse?lat=${latitude}&lon=${longitude}&format=json&accept-language=${encodeURIComponent(language)}&zoom=10`;
    const nominatimResponse = await fetch(nominatimUrl, {
      headers: {
        'Accept-Charset': 'utf-8',
        'User-Agent': 'AtmosMind-Weather/1.0',
      },
    });

    if (nominatimResponse.ok) {
      const data = await nominatimResponse.json();
      const addr = data.address || {};
      const city =
        addr.city ||
        addr.town ||
        addr.village ||
        addr.municipality ||
        addr.county ||
        '';

      if (city) {
        return {
          name: city,
          country: addr.country || undefined,
          country_code: addr.country_code?.toUpperCase() || undefined,
          admin1: addr.state || addr.province || addr.region || undefined,
          latitude,
          longitude,
        };
      }
    }
  } catch (error) {
    console.warn('Nominatim reverse geocoding failed:', error);
  }

  // Strategy 2: BigDataCloud free reverse geocoding (fallback)
  try {
    const bdcUrl = `https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=${latitude}&longitude=${longitude}&localityLanguage=${encodeURIComponent(language)}`;
    const bdcResponse = await fetch(bdcUrl, {
      headers: { 'Accept-Charset': 'utf-8' },
    });

    if (bdcResponse.ok) {
      const bdcData = await bdcResponse.json();
      const city =
        bdcData.city ||
        bdcData.locality ||
        bdcData.principalSubdivision ||
        '';

      if (city) {
        return {
          name: city,
          country: bdcData.countryName || undefined,
          country_code: bdcData.countryCode || undefined,
          admin1: bdcData.principalSubdivision || undefined,
          latitude,
          longitude,
        };
      }
    }
  } catch (error) {
    console.warn('BigDataCloud reverse geocoding failed:', error);
  }

  // All strategies failed
  return null;
}

export async function autocompleteCities(query: string, language: string) {
  return postJson<{ suggestions: Array<{ name: string; lat: number; lon: number }> }, { query: string; language: string }>(
    apiUrl('/api/autocomplete'),
    { query, language }
  );
}

export async function fetchAiWeather(city: string, language: string, unit: 'metric' | 'imperial') {
  return postJson(apiUrl('/api/ai-weather'), { city, language, unit });
}


export async function fetchForecastSummary(
  city: string,
  weather_summary: string,
  language: string,
  unit: 'metric' | 'imperial'
) {
  return postJson<{ summary: string }, { city: string; weather_summary: string; language: string; unit: 'metric' | 'imperial' }>(
    apiUrl('/api/get-forecast-summary'),
    { city, weather_summary, language, unit }
  );
}

export async function fetchCityAdvice(
  city: string,
  weather_summary: string,
  language: string,
  unit: 'metric' | 'imperial'
) {
  return postJson<{ advice: string }, { city: string; weather_summary: string; language: string; unit: 'metric' | 'imperial' }>(
    apiUrl('/api/get-city-advice'),
    { city, weather_summary, language, unit }
  );
}

export interface BatchWeatherItem {
  city: string;
  temperature: number | null;
  condition: string | null;
  weather_code: number | null;
  error: string | null;
}

export interface BatchWeatherResponse {
  results: BatchWeatherItem[];
  temperatures: Record<string, number>;
}

export async function fetchPopularWeatherBatch(
  cities: string[]
): Promise<BatchWeatherResponse> {
  return postJson<BatchWeatherResponse, { cities: string[] }>(
    apiUrl('/api/weather/batch'),
    { cities }
  );
}

export async function fetchWeatherDetail(
  latitude: number,
  longitude: number,
  language: string,
  unit: 'metric' | 'imperial',
  options?: { signal?: AbortSignal; timeoutMs?: number }
): Promise<WeatherDetailApiResponse> {
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? 45_000;
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  options?.signal?.addEventListener('abort', onExternalAbort);

  try {
    const response = await fetch(apiUrl('/api/weather/detail'), {
      method: 'POST',
      headers: JSON_HEADERS,
      body: JSON.stringify({ latitude, longitude, language, unit }),
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Weather detail request failed: ${response.status}`);
    }
    return response.json() as Promise<WeatherDetailApiResponse>;
  } finally {
    window.clearTimeout(timeoutId);
    options?.signal?.removeEventListener('abort', onExternalAbort);
  }
}

export async function fetchLifestyleIndices(
  latitude: number,
  longitude: number,
  options?: { signal?: AbortSignal; timeoutMs?: number }
): Promise<LifestyleIndices> {
  const controller = new AbortController();
  const timeoutMs = options?.timeoutMs ?? 5_000;
  const timeoutId = window.setTimeout(() => controller.abort(), timeoutMs);

  const onExternalAbort = () => controller.abort();
  options?.signal?.addEventListener('abort', onExternalAbort);

  try {
    const params = new URLSearchParams({
      latitude: String(latitude),
      longitude: String(longitude),
    });
    const response = await fetch(apiUrl(`/api/lifestyle-indices?${params.toString()}`), {
      headers: { Accept: 'application/json', 'Accept-Charset': 'utf-8' },
      signal: controller.signal,
    });
    if (!response.ok) {
      throw new Error(`Lifestyle indices request failed: ${response.status}`);
    }
    return response.json() as Promise<LifestyleIndices>;
  } finally {
    window.clearTimeout(timeoutId);
    options?.signal?.removeEventListener('abort', onExternalAbort);
  }
}
