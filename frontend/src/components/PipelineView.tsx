"use client";

import { QueueItem, SystemStats } from "@/hooks/useWebSocket";

interface Props {
  currentEpisode: QueueItem | null;
  stats: SystemStats | null;
}

const PIPELINE_STEPS = [
  { key: "scripting", agent: "Showrunner", model: "Nova 2 Lite", color: "#0EA5E9" },
  { key: "casting", agent: "Casting Director", model: "Nova Embeddings", color: "#F59E0B" },
  { key: "voicing", agent: "Voice Actor", model: "Nova 2 Sonic", color: "#10B981" },
  { key: "editing", agent: "Editor", model: "FFmpeg", color: "#A78BFA" },
];

const STATUS_ORDER = ["scripting", "casting", "voicing", "editing", "ready", "live"];

function getStepState(
  stepKey: string,
  currentStatus: string
): "done" | "active" | "pending" {
  const stepIdx = STATUS_ORDER.indexOf(stepKey);
  const currentIdx = STATUS_ORDER.indexOf(currentStatus);
  if (currentIdx < 0) return "pending";
  if (stepIdx < currentIdx) return "done";
  if (stepIdx === currentIdx) return "active";
  return "pending";
}

function formatUptime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export default function PipelineView({ currentEpisode, stats }: Props) {
  const currentStatus = currentEpisode?.status || "";

  return (
    <div className="flex flex-col h-full bg-[#080B0F]">
      {/* Header */}
      <div className="px-3 py-2 border-b border-[#1E2D3D]">
        <span className="font-barlow font-black text-[10px] tracking-[3px] text-[#4A6278] uppercase">
          Pipeline
        </span>
      </div>

      {/* Step Indicator */}
      <div className="px-4 py-4 flex-1">
        <div className="relative">
          {/* Connecting Line */}
          <div className="absolute left-[11px] top-3 bottom-3 w-px bg-[#1E2D3D]" />

          {PIPELINE_STEPS.map((step) => {
            const state = getStepState(step.key, currentStatus);
            return (
              <div key={step.key} className="flex items-start gap-3 mb-6 relative">
                {/* Step Indicator Circle */}
                <div className="relative z-10 shrink-0">
                  {state === "done" && (
                    <div className="w-[22px] h-[22px] rounded-full bg-[#10B981]/20 flex items-center justify-center">
                      <svg className="w-3 h-3 text-[#10B981]" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                  {state === "active" && (
                    <div className="w-[22px] h-[22px] rounded-full border-2 border-[#F59E0B] flex items-center justify-center animate-pulse">
                      <div className="w-2 h-2 rounded-full bg-[#F59E0B]" />
                    </div>
                  )}
                  {state === "pending" && (
                    <div className="w-[22px] h-[22px] rounded-full border border-[#1E2D3D]" />
                  )}
                </div>

                {/* Step Details */}
                <div className="min-w-0">
                  <p
                    className={`font-inter text-[12px] font-medium ${
                      state === "active"
                        ? "text-[#F59E0B]"
                        : state === "done"
                        ? "text-[#C8D6E5]"
                        : "text-[#4A6278]"
                    }`}
                  >
                    {step.agent}
                  </p>
                  <p className="font-mono text-[10px] text-[#4A6278]">{step.model}</p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-2 mt-4">
          <StatCard label="Episodes" value={stats?.episodes_count?.toString() || "0"} />
          <StatCard label="Uptime" value={stats ? formatUptime(stats.uptime_secs) : "0m"} />
          <StatCard
            label="Avg Latency"
            value={stats ? `${stats.sonic_latency_ms.toFixed(0)}ms` : "--"}
          />
          <StatCard
            label="Embed Score"
            value={stats ? stats.embed_score_avg.toFixed(2) : "--"}
          />
        </div>

        {/* Agent Model Mapping */}
        <div className="mt-4 border border-[#1E2D3D] rounded">
          <div className="px-2 py-1.5 border-b border-[#1E2D3D]">
            <span className="font-barlow font-black text-[9px] tracking-[2px] text-[#4A6278] uppercase">
              Nova Models
            </span>
          </div>
          <div className="divide-y divide-[#1E2D3D]">
            {PIPELINE_STEPS.map((step) => (
              <div key={step.key} className="flex items-center justify-between px-2 py-1.5">
                <span className="font-mono text-[10px] text-[#7A9AB5]">{step.agent}</span>
                <span
                  className="font-mono text-[9px] px-1.5 py-0.5 rounded"
                  style={{ color: step.color, backgroundColor: `${step.color}15` }}
                >
                  {step.model}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#0D1117] border border-[#1E2D3D] rounded px-2.5 py-2">
      <p className="font-barlow font-black text-[8px] tracking-[2px] text-[#4A6278] uppercase">
        {label}
      </p>
      <p className="font-mono text-[16px] text-[#C8D6E5] mt-0.5">{value}</p>
    </div>
  );
}
