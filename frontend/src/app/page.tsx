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
  const { logs, queue, nowPlaying, stats, connected } = useWebSocket();
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
      <div className="h-screen w-screen flex flex-col items-center justify-center bg-[#030B12] gap-6">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-2">
          <div className="w-3 h-3 rounded-full bg-[#0EA5E9] animate-pulse" />
          <span className="text-[#0EA5E9] font-barlow font-black text-2xl tracking-[8px] uppercase">
            NOVASTREAM
          </span>
          <div className="w-3 h-3 rounded-full bg-[#0EA5E9] animate-pulse" />
        </div>

        {/* Spinner */}
        <div className="w-12 h-12 border-4 border-[#1E2D3D] border-t-[#0EA5E9] rounded-full animate-spin" />

        {/* Status */}
        <div className="flex flex-col items-center gap-2 text-center">
          <p className="text-[#7A9AB5] text-sm font-mono">
            Waking up the broadcast server
            <span className="animate-pulse">...</span>
          </p>
          <p className="text-[#2A4060] text-xs font-mono">
            {elapsed < 10
              ? "Connecting to backend..."
              : elapsed < 30
              ? `Still starting up — ${elapsed}s elapsed`
              : `Almost there — ${elapsed}s elapsed`}
          </p>
          {elapsed > 15 && (
            <p className="text-[#1A3050] text-xs font-mono mt-1">
              First load on Render free tier can take up to 45 seconds
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
    <div className="h-screen w-screen flex flex-col overflow-hidden">
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
              className={`flex-1 py-2 font-barlow font-black text-[10px] tracking-[3px] uppercase transition-colors ${
                sidebarTab === "terminal"
                  ? "text-[#0EA5E9] border-b-2 border-[#0EA5E9]"
                  : "text-[#4A6278] hover:text-[#7A9AB5]"
              }`}
            >
              Terminal
            </button>
            <button
              onClick={() => setSidebarTab("pipeline")}
              className={`flex-1 py-2 font-barlow font-black text-[10px] tracking-[3px] uppercase transition-colors ${
                sidebarTab === "pipeline"
                  ? "text-[#0EA5E9] border-b-2 border-[#0EA5E9]"
                  : "text-[#4A6278] hover:text-[#7A9AB5]"
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
      <NewsTicker headline={nowPlaying?.headline || ""} />
    </div>
  );
}
