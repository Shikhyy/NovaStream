"use client";

import { useState, useEffect } from "react";
import { useWebSocket } from "@/hooks/useWebSocket";
import GlobalTopBar from "@/components/GlobalTopBar";
import VideoPlayer from "@/components/VideoPlayer";
import AgentTerminal from "@/components/AgentTerminal";
import EpisodeQueue from "@/components/EpisodeQueue";
import NewsTicker from "@/components/NewsTicker";
import PipelineView from "@/components/PipelineView";

export default function Home() {
  const { logs, queue, nowPlaying, stats, tickerHeadlines, connected, reconnecting, reconnectInSec } = useWebSocket();
  const [sidebarTab, setSidebarTab] = useState<"terminal" | "pipeline">("terminal");
  const [elapsed, setElapsed] = useState(0);

  // Track seconds while waiting for the backend to wake up (Render cold start)
  useEffect(() => {
    if (connected) return;
    const interval = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [connected]);

  if (!connected) {
    return (
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#030912] gap-8 overflow-hidden relative">
        {/* Expanding rings */}
        <div className="absolute w-56 h-56 rounded-full border border-[#0EA5E9]/15 animate-ring-expand" />
        <div className="absolute w-56 h-56 rounded-full border border-[#0EA5E9]/10 animate-ring-expand [animation-delay:0.85s]" />
        <div className="absolute w-56 h-56 rounded-full border border-[#0EA5E9]/8 animate-ring-expand [animation-delay:1.7s]" />

        {/* Logo */}
        <div className="relative flex flex-col items-center gap-2 z-10 animate-fade-up">
          <div className="flex items-center gap-3">
            <div className="w-2 h-2 rounded-full bg-[#0EA5E9] shadow-[0_0_8px_rgba(14,165,233,0.9)] animate-pulse" />
            <span className="text-[#0EA5E9] font-barlow font-black text-3xl tracking-[10px] uppercase [text-shadow:0_0_30px_rgba(14,165,233,0.4)]">
              NOVASTREAM
            </span>
            <div className="w-2 h-2 rounded-full bg-[#0EA5E9] shadow-[0_0_8px_rgba(14,165,233,0.9)] animate-pulse" />
          </div>
          <span className="font-barlow font-black text-[9px] tracking-[6px] text-[#2A4060] uppercase">
            Autonomous AI Broadcast
          </span>
        </div>

        {/* Spinner */}
        <div className="w-8 h-8 border-2 border-[#0EA5E9]/20 border-t-[#0EA5E9] rounded-full animate-spin z-10" />

        {/* Status card */}
        <div className="z-10 border border-[#1E2D3D] bg-[#0D1117]/80 px-6 py-3 rounded-sm flex flex-col items-center gap-1.5 min-w-[280px] animate-fade-up [animation-delay:150ms]">
          <p className="text-[#7A9AB5] text-sm font-mono flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-[#0EA5E9] animate-pulse shrink-0" />
            Waking up the broadcast server
          </p>
          <p className="text-[#2A4060] text-xs font-mono">
            {elapsed < 10
              ? "Connecting to backend..."
              : reconnecting
              ? `Reconnecting in ${reconnectInSec}s — ${elapsed}s elapsed`
              : elapsed < 30
              ? `Still starting up — ${elapsed}s elapsed`
              : `Almost there — ${elapsed}s elapsed`}
          </p>
          {elapsed > 15 && (
            <p className="text-[#1A3050] text-xs font-mono">
              Free tier cold start may take up to 45s
            </p>
          )}
        </div>
      </div>
    );
  }

  const currentEpisode = queue.find(
    (ep) => ep.episode_id === nowPlaying?.episode_id
  ) || queue.find(
    (ep) => !["ready", "live", "failed"].includes(ep.status)
  ) || null;

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#080B0F]">
      {/* Top Bar */}
      <GlobalTopBar
        stats={stats}
        connected={connected}
        episodesCount={queue.filter((e) => e.status === "live" || e.status === "ready").length}
      />

      {/* Main Content */}
      <div className="flex flex-1 min-h-0">
        {/* Video Panel */}
        <div className="flex-1 flex flex-col min-w-0 p-3 gap-3">
          <VideoPlayer nowPlaying={nowPlaying} queue={queue} />
          <EpisodeQueue queue={queue} currentEpisodeId={nowPlaying?.episode_id} />
        </div>

        {/* Sidebar */}
        <div className="w-[340px] shrink-0 border-l border-[#1E2D3D] flex flex-col">
          {/* Sidebar Tabs */}
          <div className="flex border-b border-[#1E2D3D]">
            <button
              onClick={() => setSidebarTab("terminal")}
              className={`flex-1 py-2.5 font-barlow font-black text-[10px] tracking-[3px] uppercase transition-all duration-150 ${
                sidebarTab === "terminal"
                  ? "text-[#0EA5E9] border-b-2 border-[#0EA5E9] shadow-[0_2px_8px_rgba(14,165,233,0.18)]"
                  : "text-[#4A6278] hover:text-[#7A9AB5] hover:bg-[#0D1117]/50"
              }`}
            >
              Terminal
            </button>
            <button
              onClick={() => setSidebarTab("pipeline")}
              className={`flex-1 py-2.5 font-barlow font-black text-[10px] tracking-[3px] uppercase transition-all duration-150 ${
                sidebarTab === "pipeline"
                  ? "text-[#0EA5E9] border-b-2 border-[#0EA5E9] shadow-[0_2px_8px_rgba(14,165,233,0.18)]"
                  : "text-[#4A6278] hover:text-[#7A9AB5] hover:bg-[#0D1117]/50"
              }`}
            >
              Pipeline
            </button>
          </div>

          {/* Sidebar Content */}
          <div className="flex-1 min-h-0">
            {sidebarTab === "terminal" ? (
              <AgentTerminal logs={logs} />
            ) : (
              <PipelineView currentEpisode={currentEpisode} stats={stats} />
            )}
          </div>
        </div>
      </div>

      {/* Bottom News Ticker */}
      <NewsTicker headlines={tickerHeadlines} />
    </div>
  );
}
