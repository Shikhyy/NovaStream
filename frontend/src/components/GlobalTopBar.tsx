"use client";

import { SystemStats } from "@/hooks/useWebSocket";

interface Props {
  stats: SystemStats | null;
  connected: boolean;
  episodesCount: number;
}

function formatUptime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function GlobalTopBar({ stats, connected, episodesCount }: Props) {
  return (
    <header className="h-12 bg-[#0D1117] border-b border-[#1E2D3D] flex items-center justify-between px-4 shrink-0">
      {/* Logo & Live Badge */}
      <div className="flex items-center gap-3">
        <h1 className="font-barlow font-black text-[#C8D6E5] text-lg tracking-[3px] uppercase">
          NovaStream
        </h1>
        <span className="text-[10px] font-barlow font-black tracking-[3px] text-[#4A6278] uppercase">
          24/7
        </span>
        <div className="flex items-center gap-1.5 bg-[#F43F5E]/10 px-2 py-0.5 rounded">
          <span className="w-2 h-2 rounded-full bg-[#F43F5E] animate-pulse" />
          <span className="text-[10px] font-barlow font-black tracking-[3px] text-[#F43F5E] uppercase">
            Live
          </span>
        </div>
      </div>

      {/* System Stats */}
      <div className="flex items-center gap-6 font-mono text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className="text-[#4A6278] uppercase tracking-[2px]">Uptime</span>
          <span className="text-[#C8D6E5]">
            {stats ? formatUptime(stats.uptime_secs) : "--:--:--"}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[#4A6278] uppercase tracking-[2px]">Episodes</span>
          <span className="text-[#C8D6E5]">{stats?.episodes_count ?? episodesCount}</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[#4A6278] uppercase tracking-[2px]">Latency</span>
          <span className="text-[#C8D6E5]">
            {stats ? `${stats.sonic_latency_ms.toFixed(0)}ms` : "--"}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="text-[#4A6278] uppercase tracking-[2px]">Embed</span>
          <span className="text-[#C8D6E5]">
            {stats ? stats.embed_score_avg.toFixed(2) : "--"}
          </span>
        </div>
        <div className="flex items-center gap-1.5">
          <span
            className={`w-2 h-2 rounded-full ${connected ? "bg-[#10B981]" : "bg-[#F43F5E]"}`}
          />
          <span className={`uppercase tracking-[2px] ${connected ? "text-[#10B981]" : "text-[#F43F5E]"}`}>
            {connected ? "Connected" : "Offline"}
          </span>
        </div>
      </div>
    </header>
  );
}
