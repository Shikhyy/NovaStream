"use client";

import { useRef, useEffect } from "react";
import { LogLine } from "@/hooks/useWebSocket";

interface Props {
  logs: LogLine[];
}

const AGENT_COLORS: Record<string, string> = {
  SHOWRUNNER: "bg-[#0EA5E9]",
  CASTING: "bg-[#F59E0B]",
  VOICE: "bg-[#10B981]",
  EDITOR: "bg-[#A78BFA]",
  PIPELINE: "bg-[#4A6278]",
};

const AGENT_BORDER_COLORS: Record<string, string> = {
  SHOWRUNNER: "#0EA5E9",
  CASTING:    "#F59E0B",
  VOICE:      "#10B981",
  EDITOR:     "#A78BFA",
  PIPELINE:   "#4A6278",
};

const LEVEL_COLORS: Record<string, string> = {
  info: "text-[#C8D6E5]",
  success: "text-[#10B981]",
  warn: "text-[#F59E0B]",
  error: "text-[#F43F5E]",
};

export default function AgentTerminal({ logs }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);

  useEffect(() => {
    if (autoScrollRef.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  const handleScroll = () => {
    if (!scrollRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    autoScrollRef.current = scrollHeight - scrollTop - clientHeight < 50;
  };

  return (
    <div className="flex flex-col h-full bg-[#080B0F]">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-[#1E2D3D] bg-[#060A0F]">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-[#10B981] shadow-[0_0_5px_rgba(16,185,129,0.8)] animate-pulse" />
          <span className="font-barlow font-black text-[10px] tracking-[3px] text-[#4A6278] uppercase">
            Agent Terminal
          </span>
        </div>
        <span className="font-mono text-[10px] text-[#2A4060] bg-[#0D1117] px-1.5 py-0.5 rounded">
          {logs.length}
        </span>
      </div>

      {/* Log Lines */}
      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto overflow-x-hidden px-3 py-2 space-y-0.5"
      >
        {logs.length === 0 && (
          <div className="flex items-center justify-center h-full">
            <p className="font-mono text-[11px] text-[#4A6278]/50">
              Waiting for pipeline output...
            </p>
          </div>
        )}
        {logs.map((log, i) => (
          <div
            key={i}
            className="flex items-start gap-2 font-mono text-[11px] leading-[1.7] animate-slide-in pl-2 border-l-2 hover:bg-[#0D1117]/60 rounded-r transition-colors"
            style={{ borderLeftColor: AGENT_BORDER_COLORS[log.agent_id] ?? "#2A3F4F" }}
          >
            {/* Timestamp */}
            <span className="text-[#4A6278] shrink-0 w-[52px]">
              {log.timestamp?.slice(11, 19) || ""}
            </span>

            {/* Agent Badge */}
            <span
              className={`shrink-0 px-1.5 py-0 rounded text-[9px] font-bold text-[#080B0F] uppercase tracking-[1px] ${
                AGENT_COLORS[log.agent_id] || "bg-[#4A6278]"
              }`}
            >
              {log.agent_id?.slice(0, 4) || "SYS"}
            </span>

            {/* Message */}
            <span className={`break-all ${LEVEL_COLORS[log.level] || "text-[#C8D6E5]"}`}>
              {log.level === "warn" && "⚠ "}
              {log.level === "error" && "✗ "}
              {log.message}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
