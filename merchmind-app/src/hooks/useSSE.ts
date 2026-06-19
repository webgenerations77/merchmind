import { useEffect, useRef, useCallback } from 'react';
import Constants from 'expo-constants';

const extra = Constants.expoConfig?.extra ?? {};

export function useSSE<T = unknown>(
  path: string | null,
  onMessage: (data: T) => void,
  onError?: (error: Event) => void,
) {
  const esRef = useRef<EventSource | null>(null);
  const onMessageRef = useRef(onMessage);
  const onErrorRef = useRef(onError);

  onMessageRef.current = onMessage;
  onErrorRef.current = onError;

  const connect = useCallback(() => {
    if (!path) return;

    const url = `${extra.API_BASE_URL}${path}`;
    const headers = { 'X-API-Key': extra.APP_API_KEY || '' };

    // React Native doesn't have native EventSource — use polyfill approach with fetch
    let cancelled = false;

    const fetchStream = async () => {
      try {
        const response = await fetch(url, {
          headers: headers as Record<string, string>,
        });

        if (!response.body) return;

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (!cancelled) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() ?? '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6)) as T;
                onMessageRef.current(data);
              } catch {
                // skip malformed lines
              }
            }
          }
        }
      } catch (e) {
        if (!cancelled && onErrorRef.current) {
          onErrorRef.current(e as Event);
        }
      }
    };

    fetchStream();

    return () => {
      cancelled = true;
    };
  }, [path]);

  useEffect(() => {
    const cleanup = connect();
    return () => {
      cleanup?.();
      esRef.current?.close();
    };
  }, [connect]);
}
