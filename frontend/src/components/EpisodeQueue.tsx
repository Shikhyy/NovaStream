"use client";

import { QueueItem } from "@/hooks/useWebSocket";

interface Props {
  queue: QueueItem[];
  currentEpisodeId?: string;
}

const STATUS_STYLES: Record<string, { bg: string; text: string; label: string }> = {
  live: { bg: "bg-[#F43F5E]/20", text: "text-[#F43F5E]", label: "LIVE" },
  ready: { bg: "bg-[#10B981]/20", text: "text-[#10B981]", label: "READY" },
  editing: { bg: "bg-[#F59E0B]/20", text: "text-[#F59E0B]", label: "RENDER" },
  voicing: { bg: "bg-[#F59E0B]/20", text: "text-[#F59E0B]", label: "RENDER" },
  casting: { bg: "bg-[#F59E0B]/20", text: "text-[#F59E0B]", label: "RENDER" },
  scripting: { bg: "bg-[#F59E0B]/20", text: "text-[#F59E0B]", label: "RENDER" },
  queued: { bg: "bg-[#1E2D3D]/50", text: "text-[#4A6278]", label: "QUEUED" },
  failed: { bg: "bg-[#F43F5E]/10", text: "text-[#F43F5E]/60", label: "FAIL" },
};

export default function EpisodeQueue({ queue, currentEpisodeId }: Props) {
  return (
    <div className="bg-[#0D1117] border-t border-[#1E2D3D]">
      <div className="flex items-center gap-2 px-3 py-2 overflow-x-auto scrollbar-thin">
        <span className="font-barlow font-black text-[9px] tracking-[3px] text-[#4A6278] uppercase shrink-0">
          Queue
        </span>
        <div className="w-px h-4 bg-[#1E2D3D]" />

        {queue.length === 0 && (
          <span className="font-mono text-[10px] text-[#4A6278]/50">Empty</span>
        )}

        {queue.map((ep) => {
          const style = STATUS_STYLES[ep.status] || STATUS_STYLES.queued;
          const isActive = ep.episode_id === currentEpisodeId;
          const title = ep.blueprint?.title || ep.source_headline || ep.episode_id;

          return (
            <div
              key={ep.episode_id}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded shrink-0 border transition-all duration-200 ${
                isActive
                  ? "border-[#F43F5E]/40 bg-[#F43F5E]/5 shadow-[0_0_12px_rgba(244,63,94,0.08)]"
                  : "border-[#1E2D3D] bg-[#0D1117] hover:border-[#2A4060] hover:bg-[#111820]"
              }`}
              title={title}
            >
              {/* Status Badge */}
              <span
                className={`text-[8px] font-barlow font-black tracking-[2px] uppercase px-1 py-0 rounded ${style.bg} ${style.text} ${
                  ["editing", "voicing", "casting", "scripting"].includes(ep.status)
                    ? "animate-pulse"
                    : ""
                }`}
              >
                {style.label}
              </span>

              {/* Episode Title (truncated) */}
              <span className="font-inter text-[10px] text-[#7A9AB5] max-w-[120px] truncate">
                {title}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
