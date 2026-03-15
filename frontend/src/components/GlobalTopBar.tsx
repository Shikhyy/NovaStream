"use client";

import { SystemStats } from "@/hooks/useWebSocket";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface Props {
  stats: SystemStats | null;
  connected: boolean;
  episodesCount: number;
}

function formatUptime(secs: number): string {
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  const s = secs % 60;
  return `${h.toString().padStart(2, "0")}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function StatPill({ label, value, color = "#C8D6E5" }: { label: string; value: string; color?: string }) {
  return (
    <div className="flex items-baseline gap-1">
      <span className="text-[#4A6278] uppercase tracking-[2px]">{label}</span>
      <span style={{ color }} className="tabular-nums">{value}</span>
    </div>
  );
}

export default function GlobalTopBar({ stats, connected, episodesCount }: Props) {
  const pathname = usePathname();
  const navItems = [
    { href: "/", label: "Live" },
    { href: "/episodes", label: "Episodes" },
    { href: "/status", label: "Status" },
    { href: "/about", label: "About" },
  ];

  return (
    <header className="relative h-12 bg-[#080D14] flex items-center justify-between px-4 shrink-0">
      {/* Gradient bottom border */}
      <div className="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-[#1B4A6A] to-transparent" />
      {/* Logo & Live Badge */}
      <div className="flex items-center gap-4 min-w-0">
        <Link href="/" className="font-barlow font-black text-[#C8D6E5] text-xl tracking-[4px] uppercase hover:text-[#0EA5E9] transition-all duration-200 hover:[text-shadow:0_0_20px_rgba(14,165,233,0.5)]">
          NovaStream
        </Link>
        <span className="text-[10px] font-barlow font-black tracking-[3px] text-[#2A4060] uppercase">
          24/7
        </span>
        <div className="flex items-center gap-1.5 bg-[#F43F5E]/10 border border-[#F43F5E]/25 px-2 py-0.5 rounded-sm shadow-[0_0_10px_rgba(244,63,94,0.14)]">
          <span className="w-1.5 h-1.5 rounded-full bg-[#F43F5E] shadow-[0_0_5px_rgba(244,63,94,0.9)] animate-pulse" />
          <span className="text-[10px] font-barlow font-black tracking-[3px] text-[#F43F5E] uppercase">
            Live
          </span>
        </div>

        <nav className="hidden md:flex items-center gap-1 border-l border-[#1E2D3D] pl-3">
          {navItems.map((item) => {
            const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`px-2.5 py-1 rounded text-[10px] font-barlow font-black tracking-[2px] uppercase transition-all duration-150 focus:outline-none focus:ring-2 focus:ring-[#0EA5E9] ${
                  isActive
                    ? "text-[#0EA5E9] bg-[#0EA5E9]/10 shadow-[inset_0_0_0_1px_rgba(14,165,233,0.2)]"
                    : "text-[#4A6278] hover:text-[#8AAFCC] hover:bg-[#0EA5E9]/5 hover:shadow-[0_0_8px_rgba(14,165,233,0.08)]"
                }`}
                aria-label={item.label}
                tabIndex={0}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>
                                connected
                                  ? "bg-[#10B981] shadow-[0_0_6px_rgba(16,185,129,0.8)]"
                                  : "bg-[#F43F5E] shadow-[0_0_6px_rgba(244,63,94,0.8)]"
                              }`} />
                              <span className={`font-barlow font-black tracking-[2px] text-[10px] uppercase ${
                                connected ? "text-[#10B981]" : "text-[#F43F5E]"
                              }`}>
                                {connected ? "Online" : "Offline"}
                              </span>
                            </div>
                          </div>
                        </header>
                      );
