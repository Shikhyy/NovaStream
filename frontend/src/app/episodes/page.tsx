"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import GlobalTopBar from "@/components/GlobalTopBar";
import NewsTicker from "@/components/NewsTicker";

const STATUS_COLORS: Record<string, string> = {
  live: "text-[#F43F5E]",
  ready: "text-[#10B981]",
  editing: "text-[#F59E0B]",
  voicing: "text-[#F59E0B]",
  casting: "text-[#F59E0B]",
  scripting: "text-[#F59E0B]",
  queued: "text-[#4A6278]",
  failed: "text-[#F43F5E]",
};

export default function EpisodesPage() {
  const { queue, stats, connected, nowPlaying, tickerHeadlines } = useWebSocket();

  const sortedQueue = useMemo(() => {
    return [...queue].sort((a, b) => {
      const at = new Date(a.created_at).getTime();
      const bt = new Date(b.created_at).getTime();
      return bt - at;
    });
  }, [queue]);

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#080B0F]">
      <GlobalTopBar
        stats={stats}
        connected={connected}
        episodesCount={queue.filter((e) => e.status === "live" || e.status === "ready").length}
      />

      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-6xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-barlow font-black text-[#C8D6E5] text-xl tracking-[2px] uppercase">Episode History</h2>
            <span className="font-mono text-xs text-[#4A6278]">{sortedQueue.length} total</span>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
            {sortedQueue.map((ep) => {
              const title = ep.blueprint?.title || ep.source_headline || ep.episode_id;
              const statusColor = STATUS_COLORS[ep.status] || "text-[#4A6278]";
              const isCurrent = nowPlaying?.episode_id === ep.episode_id;

              return (
                <Link
                  key={ep.episode_id}
                  href={`/episodes/${ep.episode_id}`}
                  className="block border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4 hover:border-[#0EA5E9]/60 transition-colors"
                >
                  <div className="flex items-center justify-between gap-3 mb-2">
                    <p className="font-barlow font-black text-sm tracking-[1px] text-[#C8D6E5] uppercase truncate">
                      {title}
                    </p>
                    <span className={`font-mono text-[10px] uppercase ${statusColor}`}>
                      {isCurrent ? "LIVE NOW" : ep.status}
                    </span>
                  </div>

                  <p className="font-inter text-xs text-[#7A9AB5] line-clamp-2 mb-2">{ep.source_headline}</p>

                  <div className="flex items-center justify-between font-mono text-[11px] text-[#4A6278]">
                    <span>ID: {ep.episode_id}</span>
                    <span>{new Date(ep.created_at).toLocaleString()}</span>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </main>

      <NewsTicker headlines={tickerHeadlines} />
    </div>
  );
}
