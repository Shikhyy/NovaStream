"use client";

import Link from "next/link";
import { useMemo } from "react";
import { useParams } from "next/navigation";
import { useWebSocket } from "@/hooks/useWebSocket";
import GlobalTopBar from "@/components/GlobalTopBar";
import NewsTicker from "@/components/NewsTicker";

export default function EpisodeDetailPage() {
  const params = useParams<{ episodeId: string }>();
  const { queue, stats, connected, tickerHeadlines } = useWebSocket();

  const episode = useMemo(
    () => queue.find((q) => q.episode_id === params.episodeId),
    [queue, params.episodeId]
  );

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-[#080B0F]">
      <GlobalTopBar
        stats={stats}
        connected={connected}
        episodesCount={queue.filter((e) => e.status === "live" || e.status === "ready").length}
      />

      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <Link href="/episodes" className="font-mono text-xs text-[#0EA5E9] hover:text-[#7CCEF3]">
              ← Back to Episodes
            </Link>
            <span className="font-mono text-xs text-[#4A6278]">ID: {params.episodeId}</span>
          </div>

          {!episode ? (
            <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-6 text-center">
              <p className="font-inter text-sm text-[#7A9AB5]">Episode not found in current queue yet.</p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
                <h2 className="font-barlow font-black text-xl tracking-[2px] text-[#C8D6E5] uppercase mb-2">
                  {episode.blueprint?.title || episode.source_headline}
                </h2>
                <p className="font-inter text-sm text-[#7A9AB5] mb-3">{episode.source_headline}</p>
                <div className="flex flex-wrap gap-3 font-mono text-xs text-[#4A6278]">
                  <span>Status: {episode.status}</span>
                  <span>Created: {new Date(episode.created_at).toLocaleString()}</span>
                  {episode.completed_at && <span>Completed: {new Date(episode.completed_at).toLocaleString()}</span>}
                </div>
              </div>

              <div className="border border-[#1E2D3D] bg-[#0D1117] rounded-lg p-4">
                <h3 className="font-barlow font-black text-sm tracking-[2px] text-[#C8D6E5] uppercase mb-3">Scenes</h3>
                <div className="space-y-2">
                  {(episode.blueprint?.scenes || []).map((scene) => (
                    <div key={scene.scene_number} className="border border-[#1E2D3D] bg-[#111820] rounded p-3">
                      <p className="font-mono text-xs text-[#0EA5E9] mb-1">Scene {scene.scene_number}</p>
                      <p className="font-inter text-sm text-[#C8D6E5] mb-1">{scene.visual_description}</p>
                      <p className="font-inter text-xs text-[#7A9AB5]">{scene.voiceover_script}</p>
                    </div>
                  ))}
                </div>
              </div>

              {episode.error_log.length > 0 && (
                <div className="border border-[#F43F5E]/30 bg-[#3A0F1A]/20 rounded-lg p-4">
                  <h3 className="font-barlow font-black text-sm tracking-[2px] text-[#F43F5E] uppercase mb-3">Errors</h3>
                  <ul className="space-y-1">
                    {episode.error_log.map((err, idx) => (
                      <li key={`${episode.episode_id}-err-${idx}`} className="font-mono text-xs text-[#FCA5A5] break-words">
                        {err}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </main>

      <NewsTicker headlines={tickerHeadlines} />
    </div>
  );
}
