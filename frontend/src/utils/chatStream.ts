import { apiUrl } from '../services/api';

export interface ChatStreamMessage {
  role: 'user' | 'assistant';
  content: string;
}

export interface ChatStreamContext {
  language: string;
  unit: string;
  sessionId?: string;
  cityName?: string | null;
  latitude?: number | null;
  longitude?: number | null;
}

export interface ChatStreamCallbacks {
  onStatus?: (phase: string) => void;
  onToken: (token: string) => void;
  onError?: (message: string) => void;
}

const CHAT_STREAM_TIMEOUT_MS = 120_000;
const GENERIC_STREAM_ERROR = 'Could not read the assistant response. Please try again.';

type SseEvent = {
  type?: string;
  content?: string;
  phase?: string;
  message?: string;
  reply?: string;
  error?: string;
};

type JsonChatPayload = {
  reply?: string;
  error?: string;
  message?: string;
};

function parseSseDataBlock(block: string): SseEvent | null {
  const dataLine = block
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.startsWith('data:'));

  if (!dataLine) return null;

  const payload = dataLine.slice(5).trim();
  if (!payload || payload === '[DONE]') return { type: 'done' };

  try {
    const data = JSON.parse(payload) as SseEvent;
    if (typeof data.error === 'string' && data.error.trim()) {
      return { type: 'error', error: data.error, message: data.error, reply: data.error };
    }
    return data;
  } catch {
    return { type: 'token', content: payload };
  }
}

function processSseEvent(
  event: SseEvent | null,
  callbacks: ChatStreamCallbacks,
  receivedRef: { value: boolean }
): 'done' | 'error' | 'continue' {
  if (!event) return 'continue';
  if (event.type === 'done') return 'done';

  if (event.type === 'status' && event.phase) {
    callbacks.onStatus?.(event.phase);
    return 'continue';
  }

  if (event.type === 'error' || event.error) {
    const message = event.error ?? event.reply ?? event.message ?? GENERIC_STREAM_ERROR;
    receivedRef.value = true;
    callbacks.onError?.(message);
    return 'error';
  }

  if (event.type === 'token' && event.content) {
    receivedRef.value = true;
    callbacks.onToken(event.content);
    return 'continue';
  }

  return 'continue';
}

async function consumeJsonReply(
  response: Response,
  callbacks: ChatStreamCallbacks
): Promise<void> {
  const data = (await response.json()) as JsonChatPayload;
  const text = (data.reply ?? data.error ?? data.message ?? '').trim();
  if (!text) {
    callbacks.onError?.(GENERIC_STREAM_ERROR);
    return;
  }
  callbacks.onToken(text);
}

async function consumeSseStream(
  body: ReadableStream<Uint8Array>,
  callbacks: ChatStreamCallbacks
): Promise<void> {
  const reader = body.getReader();
  const receivedRef = { value: false };
  const decoder = new TextDecoder();
  let buffer = '';
  let finished = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split('\n\n');
      buffer = events.pop() ?? '';

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;

        let outcome: 'done' | 'error' | 'continue' = 'continue';
        try {
          outcome = processSseEvent(parseSseDataBlock(rawEvent), callbacks, receivedRef);
        } catch {
          continue;
        }

        if (outcome === 'done' || outcome === 'error') {
          finished = true;
          break;
        }
      }
      
      if (finished) break;
    }

    if (buffer.trim() && !finished) {
      const outcome = processSseEvent(parseSseDataBlock(buffer), callbacks, receivedRef);
      if (outcome === 'done' || outcome === 'error') finished = true;
    }

    if (!receivedRef.value) {
      callbacks.onError?.(
        'No response received from the assistant. Is the backend running on port 8000?'
      );
    }
  } catch {
    callbacks.onError?.(GENERIC_STREAM_ERROR);
    try {
      await reader.cancel();
    } catch {
      // ignore cancel failures
    }
  } finally {
    try {
      reader.releaseLock();
    } catch {
      // ignore if already released
    }
  }
}

/**
 * POST /api/chat — handles both SSE streams and plain JSON `{ reply }` fallbacks.
 */
export async function streamChatReply(
  messages: ChatStreamMessage[],
  context: ChatStreamContext,
  callbacks: ChatStreamCallbacks,
  signal?: AbortSignal
): Promise<void> {
  const timeoutController = new AbortController();
  const timeoutId = window.setTimeout(() => timeoutController.abort(), CHAT_STREAM_TIMEOUT_MS);

  const onAbort = () => timeoutController.abort();
  signal?.addEventListener('abort', onAbort);

  try {
    const response = await fetch(apiUrl('/api/chat'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream, application/json',
        'Accept-Charset': 'utf-8',
      },
      body: JSON.stringify({
        messages,
        language: context.language,
        unit: context.unit,
        session_id: context.sessionId,
        city_name: context.cityName ?? undefined,
        latitude: context.latitude ?? undefined,
        longitude: context.longitude ?? undefined,
      }),
      signal: timeoutController.signal,
    });

    if (!response.ok) {
      throw new Error(`Chat request failed: ${response.status}`);
    }

    const contentType = response.headers.get('content-type') ?? '';

    if (contentType.includes('application/json')) {
      await consumeJsonReply(response, callbacks);
      return;
    }

    if (contentType.includes('text/html')) {
      throw new Error(
        'Chat API returned HTML instead of a stream. Set REACT_APP_API_URL=http://localhost:8000 in frontend/.env'
      );
    }

    if (!response.body) {
      throw new Error('Streaming is not supported in this browser.');
    }

    await consumeSseStream(response.body, callbacks);
  } catch (err) {
    if ((err as Error).name === 'AbortError') {
      if (signal?.aborted) throw err;
      callbacks.onError?.('The assistant took too long to respond. Please try again.');
      return;
    }
    callbacks.onError?.(
      err instanceof Error ? err.message : 'An unexpected error occurred while reading the chat stream.'
    );
  } finally {
    window.clearTimeout(timeoutId);
    signal?.removeEventListener('abort', onAbort);
  }
}
