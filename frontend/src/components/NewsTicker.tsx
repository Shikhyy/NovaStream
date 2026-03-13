"use client";

interface Props {
  headline: string;
}

export default function NewsTicker({ headline }: Props) {
  const text = headline || "NovaStream 24/7 — Autonomous AI Television — Powered by Amazon Nova";

  return (
    <div className="h-[26px] bg-white flex items-center overflow-hidden shrink-0">
      <div className="flex items-center gap-3 px-3 shrink-0">
        <span className="font-barlow font-black text-[9px] tracking-[3px] text-[#F43F5E] uppercase">
          Breaking
        </span>
        <div className="w-px h-3 bg-[#E5E7EB]" />
      </div>
      <div className="flex-1 overflow-hidden relative">
        <div className="animate-ticker whitespace-nowrap">
          <span className="font-inter text-[12px] font-medium text-[#080B0F] pr-[100vw]">
            {text}
          </span>
          <span className="font-inter text-[12px] font-medium text-[#080B0F]">
            {text}
          </span>
        </div>
      </div>
    </div>
  );
}
