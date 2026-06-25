/**
 * Helpers for cancel-safe async hooks (AbortController + monotonic request ids).
 */
export function createRequestGuard() {
  let requestId = 0;
  let abortController: AbortController | null = null;

  return {
    begin(): { requestId: number; signal: AbortSignal } {
      abortController?.abort();
      abortController = new AbortController();
      requestId += 1;
      return { requestId, signal: abortController.signal };
    },
    isLatest(id: number): boolean {
      return id === requestId;
    },
    abort(): void {
      abortController?.abort();
      abortController = null;
    },
  };
}

export const WEATHER_FETCH_TIMEOUT_MS = 8_000;
export const CITY_DETAIL_FETCH_TIMEOUT_MS = 12_000;
export const LIFESTYLE_FETCH_TIMEOUT_MS = 5_000;
export const GEOCODE_TIMEOUT_MS = 6_000;

export function abortableTimeout(signal: AbortSignal, ms: number): Promise<never> {
  return new Promise((_, reject) => {
    if (signal.aborted) {
      reject(new DOMException('Aborted', 'AbortError'));
      return;
    }
    const timer = window.setTimeout(() => {
      reject(new DOMException('Timeout', 'TimeoutError'));
    }, ms);
    const onAbort = () => {
      window.clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };
    signal.addEventListener('abort', onAbort, { once: true });
  });
}
