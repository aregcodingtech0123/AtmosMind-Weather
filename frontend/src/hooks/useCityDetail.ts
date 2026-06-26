import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchWeatherDetail } from '../services/api';
import { LifestyleIndices, WeatherData } from '../types/weather';
import { mapWeatherDetailToWeatherData } from '../utils/weatherDetailMapper';
import { CITY_DETAIL_FETCH_TIMEOUT_MS, createRequestGuard } from '../utils/requestGuard';

interface UseCityDetailReturn {
  weatherData: WeatherData | null;
  lifestyleIndices: LifestyleIndices | null;
  loading: boolean;
  error: string | null;
  lifestyleError: string | null;
  refetch: () => void;
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
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lifestyleError, setLifestyleError] = useState<string | null>(null);
  const guardRef = useRef(createRequestGuard());

  const fetchData = useCallback(async () => {
    if (latitude === null || longitude === null) {
      guardRef.current.abort();
      setWeatherData(null);
      setLifestyleIndices(null);
      setLoading(false);
      setError(null);
      setLifestyleError(null);
      return;
    }

    const { requestId, signal } = guardRef.current.begin();
    setLoading(true);
    setError(null);
    setLifestyleError(null);
    setWeatherData(null);
    setLifestyleIndices(null);

    try {
      const result = await fetchWeatherDetail(latitude, longitude, language, unit, {
        signal,
        timeoutMs: CITY_DETAIL_FETCH_TIMEOUT_MS,
      });

      if (!guardRef.current.isLatest(requestId) || signal.aborted) {
        return;
      }

      setWeatherData(mapWeatherDetailToWeatherData(result.weather));
      setLifestyleIndices(result.lifestyle_indices);

      const lifestyle = result.lifestyle_indices;
      const lifestyleMissing =
        lifestyle.aqi_value == null &&
        lifestyle.uv_index == null &&
        lifestyle.pollen.level === 'unknown' &&
        lifestyle.visibility_meters == null;

      if (lifestyleMissing) {
        setLifestyleError(String(t('messages.failedToLoadLifestyleIndices')));
      }
    } catch (err) {
      if (!guardRef.current.isLatest(requestId) || signal.aborted) {
        return;
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }

      console.error('City detail fetch error:', err);
      const isTimeout = err instanceof DOMException && err.name === 'TimeoutError';
      setError(
        String(
          isTimeout ? t('messages.weatherFetchTimeout') : t('messages.failedToLoadWeather')
        )
      );
      setWeatherData(null);
      setLifestyleIndices(null);
    } finally {
      if (guardRef.current.isLatest(requestId)) {
        setLoading(false);
      }
    }
  }, [latitude, longitude, language, unit, t]);

  useEffect(() => {
    const guard = guardRef.current;
    fetchData();
    return () => {
      guard.abort();
    };
  }, [fetchData]);

  return {
    weatherData,
    lifestyleIndices,
    loading,
    error,
    lifestyleError,
    refetch: fetchData,
  };
}
