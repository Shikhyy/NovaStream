"use client";

import { useState, useEffect } from "react";
import { TickerItem } from "@/hooks/useWebSocket";

interface Props {
  headlines: TickerItem[];
}

const CHIP_STYLES: Record<string, string> = {
  finance: "bg-emerald-500 text-white",
  space:   "bg-violet-500 text-white",
  politics:"bg-blue-500 text-white",
  crime:   "bg-red-500 text-white",
  health:  "bg-pink-500 text-white",
  climate: "bg-amber-500 text-white",
  tech:    "bg-cyan-500 text-white",
  news:    "bg-[#6B7280] text-white",
};

const FALLBACK_ITEMS: TickerItem[] = [
  { text: "NovaStream 24/7 — Autonomous AI Television", category: "news",  addedAt: 0 },
  { text: "Powered by Amazon Nova",                    category: "tech",  addedAt: 0 },
  { text: "Broadcast Intelligence Pipeline Active",    category: "tech",  addedAt: 0 },
];

function formatAge(addedAt: number): string {
  if (!addedAt) return "";
  const diffMins = Math.floor((Date.now() - addedAt) / 60000);
  if (diffMins < 1)  return "just now";
  if (diffMins < 60) return `${diffMins}m`;
  return `${Math.floor(diffMins / 60)}h`;
}

const BATCH_SIZE        = 3;
const BATCH_INTERVAL_MS = 12000;

export default function NewsTicker({ headlines }: Props) {
  const items       = headlines.length > 0 ? headlines : FALLBACK_ITEMS;
  const totalBatches = Math.ceil(items.length / BATCH_SIZE);
  const [batchIndex, setBatchIndex] = useState(0);

  useEffect(() => {
    if (totalBatches <= 1) {
      setBatchIndex(0);
      return;
    }
    const timer = setInterval(() => {
      setBatchIndex((prev) => (prev + 1) % totalBatches);
    }, BATCH_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [totalBatches]);

  const safeBatch  = batchIndex % Math.max(1, totalBatches);
  const batchStart = safeBatch * BATCH_SIZE;
  const batch      = items.slice(batchStart, batchStart + BATCH_SIZE);
  const dots       = totalBatches > 1 ? Array.from({ length: totalBatches }, (_, i) => i) : [];

  return (
    <div className="h-[30px] bg-white/95 border-t border-[#E5E7EB] flex items-center overflow-hidden shrink-0 relative z-20">
      {/* Label + batch progress dots */}
      <div className="flex items-center gap-2 px-3 shrink-0">
        <span className="font-barlow font-black text-[9px] tracking-[3px] text-[#F43F5E] uppercase">
          Breaking
        </span>
        {dots.length > 0 && (
          <div className="flex gap-0.5">
            {dots.map((i) => (
              <div
                key={i}
                className={`w-1 h-1 rounded-full transition-colors duration-300 ${
                  i === safeBatch ? "bg-[#F43F5E]" : "bg-[#D1D5DB]"
                }`}
              />
            ))}
          </div>
        )}
        <div className="w-px h-3 bg-[#E5E7EB]" />
      </div>

      {/* Scrolling crawl — key restarts the animation on each batch */}
      <div className="flex-1 overflow-hidden relative">
        <div key={`tb-${safeBatch}`} className="animate-ticker whitespace-nowrap">
          {[...batch, ...batch].map((item, i) => (
            <span key={i} className="inline-flex items-center gap-1.5 pr-12">
              <span
                className={`inline-block px-1 rounded text-[8px] font-barlow font-black tracking-[1px] uppercase leading-4 ${
                  CHIP_STYLES[item.category] ?? CHIP_STYLES.news
                }`}
              >
                {item.category}
              </span>
              <span className="font-inter text-[12px] font-medium text-[#080B0F]">
                {item.text}
              </span>
              {item.addedAt > 0 && (
                <span className="font-mono text-[10px] text-[#9CA3AF]">
                  {formatAge(item.addedAt)}
                </span>
              )}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
