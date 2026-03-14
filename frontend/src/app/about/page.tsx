"use client";

import GlobalTopBar from "@/components/GlobalTopBar";
import NewsTicker from "@/components/NewsTicker";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function AboutPage() {
  const { queue, stats, connected, tickerHeadlines } = useWebSocket();

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#080B0F]">
      <GlobalTopBar
        stats={stats}
        connected={connected}
        episodesCount={queue.filter((e) => e.status === "live" || e.status === "ready").length}
      />

      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-5xl mx-auto space-y-4">
          <h2 className="font-barlow font-black text-[#C8D6E5] text-xl tracking-[2px] uppercase">About NovaStream</h2>

          <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
            <p className="font-inter text-sm text-[#C8D6E5] leading-relaxed">
              NovaStream is an autonomous AI television pipeline that discovers breaking headlines, generates a scripted episode,
              matches scene visuals, synthesizes narration, renders a final video, and broadcasts it live.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">Backend</p>
              <p className="font-inter text-sm text-[#7A9AB5]">FastAPI, async pipeline, FFmpeg rendering, WebSocket broadcast.</p>
            </div>
            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">Frontend</p>
              <p className="font-inter text-sm text-[#7A9AB5]">Next.js live control room with queue, terminal, and playback overlays.</p>
            </div>
            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">AI Stack</p>
              <p className="font-inter text-sm text-[#7A9AB5]">Amazon Nova Lite, Nova Sonic, and smart Pexels scene matching with fallback safety modes.</p>
            </div>
            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
              <p className="font-barlow font-black text-xs tracking-[2px] text-[#4A6278] uppercase mb-2">Storage</p>
              <p className="font-inter text-sm text-[#7A9AB5]">Supabase object storage for episode outputs with local fallback support.</p>
            </div>
          </div>
        </div>
      </main>

      <NewsTicker headlines={tickerHeadlines} />
    </div>
  );
}
