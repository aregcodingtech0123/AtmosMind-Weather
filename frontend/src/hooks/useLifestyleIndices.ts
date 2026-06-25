import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { fetchLifestyleIndices } from '../services/api';
import { LifestyleIndices } from '../types/weather';
import { createEmptyLifestyleIndices } from '../utils/lifestyleUtils';
import { LIFESTYLE_FETCH_TIMEOUT_MS, createRequestGuard } from '../utils/requestGuard';

interface UseLifestyleIndicesReturn {
  data: LifestyleIndices | null;
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useLifestyleIndices(
  latitude: number | null,
  longitude: number | null
): UseLifestyleIndicesReturn {
  const { t } = useTranslation();
  const [data, setData] = useState<LifestyleIndices | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const guardRef = useRef(createRequestGuard());

  const fetchData = useCallback(async () => {
    if (latitude === null || longitude === null) {
      guardRef.current.abort();
      setData(null);
      setLoading(false);
      setError(null);
      return;
    }

    const { requestId, signal } = guardRef.current.begin();
    setLoading(true);
    setError(null);
    setData(null);

    try {
      const result = await fetchLifestyleIndices(latitude, longitude, {
        signal,
        timeoutMs: LIFESTYLE_FETCH_TIMEOUT_MS,
      });
      if (!guardRef.current.isLatest(requestId) || signal.aborted) {
        return;
      }
      setData(result);
    } catch (err) {
      if (!guardRef.current.isLatest(requestId) || signal.aborted) {
        return;
      }
      if (err instanceof DOMException && err.name === 'AbortError') {
        return;
      }
      console.error('Lifestyle indices fetch error:', err);
      setData(createEmptyLifestyleIndices(latitude, longitude));
      setError(String(t('messages.failedToLoadLifestyleIndices')));
    } finally {
      if (guardRef.current.isLatest(requestId)) {
        setLoading(false);
      }
    }
  }, [latitude, longitude, t]);

  useEffect(() => {
    fetchData();
    return () => {
      guardRef.current.abort();
    };
  }, [fetchData]);

  return { data, loading, error, refetch: fetchData };
}
