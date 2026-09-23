import { useEffect, useRef, useState } from "react";
import type { WsEvent } from "../types";

export function useJobSocket(jobId: string | undefined) {
  const [events, setEvents] = useState<WsEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!jobId) return;
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/jobs/${jobId}`);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (msg) => {
      try {
        const event: WsEvent = JSON.parse(msg.data);
        setEvents((prev) => [...prev, event]);
      } catch {
        /* ignore malformed */
      }
    };

    return () => ws.close();
  }, [jobId]);

  return { events, connected };
}
