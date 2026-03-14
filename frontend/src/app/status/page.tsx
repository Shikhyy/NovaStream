"use client";

import GlobalTopBar from "@/components/GlobalTopBar";
import NewsTicker from "@/components/NewsTicker";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function StatusPage() {
  const { queue, stats, connected, nowPlaying, tickerHeadlines, reconnecting, reconnectInSec } = useWebSocket();

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#080B0F]">
      <GlobalTopBar
        stats={stats}
        connected={connected}
        episodesCount={queue.filter((e) => e.status === "live" || e.status === "ready").length}
      />

      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-5xl mx-auto">
          <h2 className="font-barlow font-black text-[#C8D6E5] text-xl tracking-[2px] uppercase mb-4">System Status</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">WebSocket</p>
              <p className={`font-mono text-sm ${connected ? "text-[#10B981]" : "text-[#F43F5E]"}`}>
                {connected ? "Connected" : "Disconnected"}
              </p>
              {!connected && reconnecting && (
                <p className="font-mono text-xs text-[#7A9AB5] mt-1">Reconnecting in {reconnectInSec}s</p>
              )}
            </div>

            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">Current Episode</p>
              <p className="font-mono text-sm text-[#C8D6E5]">{nowPlaying?.episode_id || "None"}</p>
              <p className="font-inter text-xs text-[#7A9AB5] mt-1">{nowPlaying?.headline || "Waiting for live episode"}</p>
            </div>

            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">Queue Size</p>
              <p className="font-mono text-sm text-[#C8D6E5]">{queue.length}</p>
            </div>

            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">Episodes Produced</p>
              <p className="font-mono text-sm text-[#C8D6E5]">{stats?.episodes_count ?? 0}</p>
            </div>
          </div>
        </div>
      </main>

      <NewsTicker headlines={tickerHeadlines} />
    </div>
  );
}
