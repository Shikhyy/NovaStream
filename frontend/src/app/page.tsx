"use client";

import { useState } from "react";
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
