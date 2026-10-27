import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchWeatherDetail } from '../services/api';
import type { ResponseMeta } from '../types/resilience';
import { LifestyleIndices, WeatherData } from '../types/weather';
import { mapWeatherDetailToWeatherData } from '../utils/weatherDetailMapper';
import { CITY_DETAIL_FETCH_TIMEOUT_MS, createRequestGuard } from '../utils/requestGuard';

interface UseCityDetailReturn {
  weatherData: WeatherData | null;
  lifestyleIndices: LifestyleIndices | null;
  detailMeta: ResponseMeta | null;
  loading: boolean;
  error: string | null;
  lifestyleError: string | null;
  refetch: (options?: { force?: boolean }) => void;
}

/**
 * Single backend-backed fetch for city detail pages.
 * Replaces direct Open-Meteo flatbuffer calls in the browser.
 */
export function useCityDetail(
  latitude: number | null,
  longitude: number | null,
  language: string,
  unit: 'metric' | 'imperial'
): UseCityDetailReturn {
  const { t } = useTranslation();
  const [weatherData, setWeatherData] = useState<WeatherData | null>(null);
  const [lifestyleIndices, setLifestyleIndices] = useState<LifestyleIndices | null>(null);
  const [detailMeta, setDetailMeta] = useState<ResponseMeta | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lifestyleError, setLifestyleError] = useState<string | null>(null);
  const guardRef = useRef(createRequestGuard());

  const fetchData = useCallback(
    async (options?: { force?: boolean }) => {
      if (latitude === null || longitude === null) {
        guardRef.current.abort();
        setWeatherData(null);
        setLifestyleIndices(null);
        setDetailMeta(null);
        setLoading(false);
        setError(null);
        setLifestyleError(null);
        return;
      }

      const { requestId, signal } = guardRef.current.begin();
      setLoading(true);
      setError(null);
      setLifestyleError(null);

      try {
        const result = await fetchWeatherDetail(latitude, longitude, language, unit, {
          signal,
          timeoutMs: CITY_DETAIL_FETCH_TIMEOUT_MS,
          forceRefresh: options?.force,
        });

        if (!guardRef.current.isLatest(requestId) || signal.aborted) {
          return;
        }

        setWeatherData(mapWeatherDetailToWeatherData(result.weather));
        setLifestyleIndices(result.lifestyle_indices);
        setDetailMeta(result.meta ?? null);

        const status = result.meta?.data_status;
        const hasCurrentWeather =
          result.weather?.current != null &&
          result.weather.current.temperature != null &&
          Number.isFinite(result.weather.current.temperature);

        if (status === 'unavailable' && !hasCurrentWeather) {
          setError(String(t('weather.unavailable')));
        }
      } catch (err) {
        if (!guardRef.current.isLatest(requestId) || signal.aborted) {
          return;
        }
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }

        console.error('City detail fetch error:', err);
        if (err instanceof Error && err.message === 'data_unavailable') {
          setError(String(t('weather.unavailable')));
          setWeatherData(null);
          setLifestyleIndices(null);
          setDetailMeta(null);
          return;
        }

        const isTimeout = err instanceof DOMException && err.name === 'TimeoutError';
        setError(
          String(
            isTimeout ? t('messages.weatherFetchTimeout') : t('messages.failedToLoadWeather')
          )
        );
        setWeatherData(null);
        setLifestyleIndices(null);
        setDetailMeta(null);
      } finally {
        if (guardRef.current.isLatest(requestId)) {
          setLoading(false);
        }
      }
    },
    [latitude, longitude, language, unit, t]
  );

  useEffect(() => {
    const guard = guardRef.current;
    void fetchData();
    return () => {
      guard.abort();
    };
  }, [fetchData]);

  const refetch = useCallback(
    (options?: { force?: boolean }) => {
      void fetchData(options);
    },
    [fetchData]
  );

  return {
    weatherData,
    lifestyleIndices,
    detailMeta,
    loading,
    error,
    lifestyleError,
    refetch,
  };
}
