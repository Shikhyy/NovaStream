"use client";

import GlobalTopBar from "@/components/GlobalTopBar";
import NewsTicker from "@/components/NewsTicker";
import { useWebSocket } from "@/hooks/useWebSocket";

export default function AboutPage() {
  const { queue = [], stats, connected, tickerHeadlines } = useWebSocket();

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#080B0F]">
      <GlobalTopBar
        stats={stats}
        connected={connected}
        episodesCount={Array.isArray(queue) ? queue.filter((e) => e.status === "live" || e.status === "ready").length : 0}
      />

      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-5xl mx-auto space-y-4">
          <h2 className="font-barlow font-black text-[#C8D6E5] text-xl tracking-[2px] uppercase">About NovaStream</h2>

          <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
            <p className="font-inter text-base text-[#C8D6E5] leading-relaxed mb-2">
              <span className="font-barlow font-black text-lg text-[#C8D6E5]">NovaStream</span> is a fully autonomous, AI-powered television network. It continuously monitors the internet for breaking news, transforms headlines into cinematic short-form video episodes—complete with scripted scenes, voiceover narration, and matched stock footage—then broadcasts them live, 24/7, with zero human intervention.
            </p>
            <ul className="list-disc pl-5 text-[#C8D6E5] text-sm mb-2">
              <li>End-to-end agentic media pipeline powered by Amazon Nova foundation models</li>
              <li>Live, always-on broadcast—no manual operation required</li>
              <li>Episodes are generated, voiced, edited, and streamed automatically</li>
            </ul>
            <a href="https://novaaastream.vercel.app" target="_blank" rel="noopener" className="text-[#00C6AE] underline text-sm">View the live channel</a>
          </div>

          <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
            <h3 className="font-barlow font-black text-[#C8D6E5] text-md uppercase mb-2">How It Works</h3>
            <ol className="list-decimal pl-5 text-[#C8D6E5] text-sm">
              <li>Fetches breaking news headlines from the live web</li>
              <li>Produces a fully scripted, multi-scene episode using Amazon Nova 2 Lite</li>
              <li>Voices the narration scene-by-scene using Amazon Nova 2 Sonic (TTS)</li>
              <li>Casts matching cinematic stock footage via the Pexels API</li>
              <li>Edits everything into a final broadcast-ready video with FFmpeg</li>
              <li>Broadcasts the episode live to a web player over WebSockets</li>
            </ol>
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
          <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4 mt-4">
            <h3 className="font-barlow font-black text-[#C8D6E5] text-md uppercase mb-2">Unique Features</h3>
            <ul className="list-disc pl-5 text-[#C8D6E5] text-sm">
              <li>Autonomous operation—no manual intervention</li>
              <li>24/7 live broadcast</li>
              <li>AI-driven scripting, narration, and editing</li>
              <li>Real-time news adaptation</li>
              <li>Modern, interactive control room UI</li>
            </ul>
          </div>
        </div>
      </main>

      <NewsTicker headlines={tickerHeadlines} />
    </div>
  );
}
}
