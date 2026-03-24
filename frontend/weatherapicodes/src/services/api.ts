const API_BASE = (process.env.REACT_APP_API_URL ?? '').replace(/\/$/, '');

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
  latitude: number;
  longitude: number;
}

export async function geocodeCity(name: string, language: string, count = 1): Promise<GeoSearchResult[]> {
  const response = await fetch(
    `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(
      name
    )}&count=${count}&language=${encodeURIComponent(language)}&format=json`,
    { headers: { 'Accept-Charset': 'utf-8' } }
  );
  if (!response.ok) return [];
  const data = (await response.json()) as { results?: GeoSearchResult[] };
  return data.results ?? [];
}

export async function reverseGeocode(
  latitude: number,
  longitude: number,
  language: string
): Promise<GeoSearchResult | null> {
  const response = await fetch(
    `https://geocoding-api.open-meteo.com/v1/reverse?latitude=${encodeURIComponent(
      String(latitude)
    )}&longitude=${encodeURIComponent(String(longitude))}&language=${encodeURIComponent(language)}&format=json`,
    { headers: { 'Accept-Charset': 'utf-8' } }
  );
  if (!response.ok) return null;
  const data = (await response.json()) as { results?: GeoSearchResult[] };
  return data.results?.[0] ?? null;
}

export async function autocompleteCities(query: string, language: string) {
  return postJson<{ suggestions: Array<{ name: string; lat: number; lon: number }> }, { query: string; language: string }>(
    `${API_BASE}/api/autocomplete`,
    { query, language }
  );
}

export async function fetchAiWeather(city: string, language: string, unit: 'metric' | 'imperial') {
  return postJson(`${API_BASE}/api/ai-weather`, { city, language, unit });
}

export async function fetchBatchWeather(cities: string[], language: string) {
  return postJson<{ results?: Array<{ city: string; temperature?: number; condition?: string; weather_code?: number }>; temperatures?: Record<string, number> }, { cities: string[]; language: string }>(
    `${API_BASE}/api/weather/batch`,
    { cities, language }
  );
}

export async function fetchForecastSummary(
  city: string,
  weather_summary: string,
  language: string,
  unit: 'metric' | 'imperial'
) {
  return postJson<{ summary: string }, { city: string; weather_summary: string; language: string; unit: 'metric' | 'imperial' }>(
    `${API_BASE}/api/get-forecast-summary`,
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
    `${API_BASE}/api/get-city-advice`,
    { city, weather_summary, language, unit }
  );
}
