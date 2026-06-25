import { useCityDetail } from './useCityDetail';

/**
 * Weather hook backed by POST /api/weather/detail (no direct Open-Meteo calls).
 * For lifestyle indices too, use `useCityDetail` directly to avoid duplicate requests.
 */
export const useWeather = (
  latitude: number | null,
  longitude: number | null,
  language: string,
  unit: 'metric' | 'imperial'
) => {
  const { weatherData, loading, error, refetch } = useCityDetail(
    latitude,
    longitude,
    language,
    unit
  );
  return { weatherData, loading, error, refetch };
};
