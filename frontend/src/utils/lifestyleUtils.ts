import { LifestyleIndices } from '../types/weather';

/** Degraded shell returned when the lifestyle API is unreachable — cards render unavailable state. */
export function createEmptyLifestyleIndices(
  latitude: number,
  longitude: number
): LifestyleIndices {
  return {
    latitude,
    longitude,
    timezone: null,
    observed_at: null,
    european_aqi: null,
    us_aqi: null,
    aqi_value: null,
    aqi_standard: 'none',
    aqi_category: 'unknown',
    uv_index: null,
    uv_category: 'unknown',
    pollen: {
      birch: null,
      grass: null,
      ragweed: null,
      level: 'unknown',
    },
    visibility_meters: null,
    dew_point_celsius: null,
  };
}

export function isPollenUnavailable(data: LifestyleIndices): boolean {
  const { pollen } = data;
  return (
    pollen.level === 'unknown' &&
    pollen.birch == null &&
    pollen.grass == null &&
    pollen.ragweed == null
  );
}

export function isVisibilityUnavailable(data: LifestyleIndices): boolean {
  return data.visibility_meters == null && data.dew_point_celsius == null;
}
