import { useCallback, useEffect, useRef } from 'react';

type MessageHandler = (data: unknown) => void;

export function useWebSocket(handlers: Record<string, MessageHandler>) {
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectRef = useRef<number>(0);

  const connect = useCallback(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const baseUrl = window.location.host;
    const url = `${protocol}//${baseUrl}/ws/pipeline`;

    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      reconnectRef.current = 0;
      ws.send(JSON.stringify({ type: 'ping' }));
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        const handler = handlers[msg.type];
        if (handler) handler(msg.data);
      } catch {
        // ignore parse errors
      }
    };

    ws.onclose = () => {
      const delay = Math.min(1000 * 2 ** reconnectRef.current, 30000);
      reconnectRef.current += 1;
      setTimeout(connect, delay);
    };

    ws.onerror = () => {
      ws.close();
    };
  }, [handlers]);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((data: unknown) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send };
}
