"use client";

import { useEffect, useRef, useState, useCallback } from "react";

export interface LogLine {
  type: "LOG_LINE";
  timestamp: string;
  agent_id: string;
  level: string;
  message: string;
}

export interface QueueItem {
  episode_id: string;
  status: string;
  source_headline: string;
  blueprint?: {
    title: string;
    tone: string;
    scenes: {
      scene_number: number;
      visual_description: string;
      voiceover_script: string;
      duration_seconds: number;
    }[];
  };
  scene_assets: { scene_number: number; video_url: string; similarity_score: number }[];
  audio_files: string[];
  video_url?: string;
  created_at: string;
  completed_at?: string;
  error_log: string[];
}

export interface NowPlaying {
  type: "NOW_PLAYING";
  video_url: string;
  episode_id: string;
  title: string;
  headline: string;
}

export interface SystemStats {
  type: "SYSTEM_STATS";
  uptime_secs: number;
  episodes_count: number;
  sonic_latency_ms: number;
  embed_score_avg: number;
}

interface WSState {
  logs: LogLine[];
  queue: QueueItem[];
  nowPlaying: NowPlaying | null;
  stats: SystemStats | null;
  connected: boolean;
  reconnecting: boolean;
  reconnectInSec: number;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function buildWsUrl(): string {
  const rawWs = (process.env.NEXT_PUBLIC_WS_URL || "").trim();

  if (rawWs) {
    const base = rawWs.replace(/\/+$/, "");
    return base.endsWith("/ws/broadcast") ? base : `${base}/ws/broadcast`;
  }

  const fromApi = API_URL.replace(/^http:/, "ws:").replace(/^https:/, "wss:").replace(/\/+$/, "");
  return `${fromApi}/ws/broadcast`;
}

const WS_URL = buildWsUrl();

export function useWebSocket() {
  const [state, setState] = useState<WSState>({
    logs: [],
    queue: [],
    nowPlaying: null,
    stats: null,
    connected: false,
    reconnecting: false,
    reconnectInSec: 0,
  });

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeout = useRef<NodeJS.Timeout | null>(null);
  const reconnectCountdown = useRef<NodeJS.Timeout | null>(null);
  const reconnectDelay = useRef(1000);

  const clearReconnectTimers = useCallback(() => {
    if (reconnectTimeout.current) {
      clearTimeout(reconnectTimeout.current);
      reconnectTimeout.current = null;
    }
    if (reconnectCountdown.current) {
      clearInterval(reconnectCountdown.current);
      reconnectCountdown.current = null;
    }
  }, []);

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    try {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        clearReconnectTimers();
        setState((s) => ({ ...s, connected: true, reconnecting: false, reconnectInSec: 0 }));
        reconnectDelay.current = 1000;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);

          setState((prev) => {
            switch (msg.type) {
              case "LOG_LINE":
                return {
                  ...prev,
                  logs: [...prev.logs.slice(-200), msg as LogLine],
                };
              case "QUEUE_UPDATE":
                return { ...prev, queue: msg.queue || [] };
              case "NOW_PLAYING":
                return { ...prev, nowPlaying: msg as NowPlaying };
              case "SYSTEM_STATS":
                return { ...prev, stats: msg as SystemStats };
              default:
                return prev;
            }
          });
        } catch {
          // ignore parse errors
        }
      };

      ws.onclose = () => {
        const delayMs = reconnectDelay.current;
        const delaySec = Math.max(1, Math.ceil(delayMs / 1000));

        setState((s) => ({
          ...s,
          connected: false,
          reconnecting: true,
          reconnectInSec: delaySec,
        }));

        if (reconnectCountdown.current) {
          clearInterval(reconnectCountdown.current);
        }
        reconnectCountdown.current = setInterval(() => {
          setState((prev) => ({
            ...prev,
            reconnectInSec: Math.max(0, prev.reconnectInSec - 1),
          }));
        }, 1000);

        // Exponential backoff reconnect
        reconnectTimeout.current = setTimeout(() => {
          reconnectDelay.current = Math.min(reconnectDelay.current * 2, 30000);
          connect();
        }, delayMs);
      };

      ws.onerror = () => {
        ws.close();
      };
    } catch {
      // retry
      setState((s) => ({ ...s, connected: false, reconnecting: true }));
      reconnectTimeout.current = setTimeout(connect, reconnectDelay.current);
    }
  }, [clearReconnectTimers]);

  useEffect(() => {
    connect();
    return () => {
      clearReconnectTimers();
      wsRef.current?.close();
    };
  }, [connect, clearReconnectTimers]);

  return state;
}
