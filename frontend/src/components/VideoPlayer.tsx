"use client";

import { useRef, useEffect, useState } from "react";
import { NowPlaying, QueueItem } from "@/hooks/useWebSocket";

interface Props {
  nowPlaying: NowPlaying | null;
  queue?: QueueItem[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type PlaybackState = "idle" | "loading" | "playing" | "buffering" | "stalled" | "error";

export default function VideoPlayer({ nowPlaying }: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [muted, setMuted] = useState(true);
  const [playFailed, setPlayFailed] = useState(false);
  const [playbackState, setPlaybackState] = useState<PlaybackState>("idle");
  const [displaySrc, setDisplaySrc] = useState("");
  const [isTransitioning, setIsTransitioning] = useState(false);

  const videoSrc = nowPlaying?.video_url
    ? nowPlaying.video_url.startsWith("http")
      ? nowPlaying.video_url
      : `${API_BASE}${nowPlaying.video_url}`
    : "";

  // Ensure muted is set via DOM (React's muted prop has a known quirk)
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = true;
    }
  }, []);

  useEffect(() => {
    if (!videoSrc) {
      setDisplaySrc("");
      setPlaybackState("idle");
      setPlayFailed(false);
      return;
    }

    setPlaybackState("loading");
    const preloadVideo = document.createElement("video");
    let cancelled = false;

    preloadVideo.preload = "auto";
    preloadVideo.src = videoSrc;
    preloadVideo.muted = true;
    preloadVideo.playsInline = true;

    preloadVideo.oncanplay = () => {
      if (cancelled) return;
      setIsTransitioning(true);
      setDisplaySrc(videoSrc);
      window.setTimeout(() => {
        if (!cancelled) setIsTransitioning(false);
      }, 220);
    };

    preloadVideo.onerror = () => {
      if (cancelled) return;
      setPlaybackState("error");
      setPlayFailed(true);
      setIsTransitioning(false);
    };

    preloadVideo.load();

    return () => {
      cancelled = true;
    };
  }, [videoSrc]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || !displaySrc) return;
    video.src = displaySrc;
    video.muted = muted;
    video.play().then(() => {
      setPlayFailed(false);
      setPlaybackState("playing");
    }).catch(() => {
      setPlayFailed(true);
      setPlaybackState("error");
    });
  }, [displaySrc, muted]);

  const handleUnmute = () => {
    setMuted(false);
    if (videoRef.current) {
      videoRef.current.muted = false;
    }
  };

  const handleClickToPlay = () => {
    setPlayFailed(false);
    videoRef.current?.play().then(() => {
      setPlaybackState("playing");
    }).catch(() => {
      setPlayFailed(true);
      setPlaybackState("error");
    });
  };

  const statusLabel = {
    loading: "Loading feed",
    buffering: "Buffering",
    stalled: "Network stalled",
    error: "Playback error",
  } as const;

  const showStatusOverlay = videoSrc && !playFailed && ["loading", "buffering", "stalled"].includes(playbackState);

  return (
    <div className="relative w-full bg-black rounded-lg overflow-hidden" style={{ aspectRatio: "16/9" }}>
      {/* Video Element */}
      <video
        ref={videoRef}
        className={`w-full h-full object-cover transition-opacity duration-300 ${isTransitioning ? "opacity-80" : "opacity-100"}`}
        autoPlay
        muted
        playsInline
        onLoadedData={() => setPlaybackState("loading")}
        onPlaying={() => setPlaybackState("playing")}
        onWaiting={() => setPlaybackState("buffering")}
        onStalled={() => setPlaybackState("stalled")}
        onError={() => setPlaybackState("error")}
        onEnded={() => {
          // Auto-advance handled by backend NOW_PLAYING messages
        }}
      />

      {/* Scanline Overlay */}
      <div
        className="absolute inset-0 pointer-events-none"
        style={{
          background: "repeating-linear-gradient(0deg, transparent, transparent 3px, rgba(0,0,0,0.08) 3px, rgba(0,0,0,0.08) 4px)",
        }}
      />

      {/* Playback status overlay */}
      {showStatusOverlay && (
        <div className="absolute inset-0 z-10 flex items-center justify-center bg-black/20 pointer-events-none">
          <div className="bg-[#080B0F]/85 border border-[#1E2D3D] px-4 py-2 rounded flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-[#0EA5E9] animate-pulse" />
            <span className="font-mono text-[11px] tracking-[1px] text-[#8FAFC8] uppercase">
              {statusLabel[playbackState as keyof typeof statusLabel] || "Loading feed"}
            </span>
          </div>
        </div>
      )}

      {/* Click-to-play overlay (shown when autoplay was blocked) */}
      {playFailed && videoSrc && (
        <button
          className="absolute inset-0 flex flex-col items-center justify-center bg-black/60 z-20"
          onClick={handleClickToPlay}
        >
          <div className="w-16 h-16 rounded-full border-2 border-[#0EA5E9] flex items-center justify-center mb-3">
            <svg className="w-7 h-7 text-[#0EA5E9] ml-1" fill="currentColor" viewBox="0 0 24 24">
              <path d="M8 5v14l11-7z" />
            </svg>
          </div>
          <p className="font-barlow font-black text-[#C8D6E5] text-xs tracking-[3px] uppercase">
            Click to Play
          </p>
        </button>
      )}

      {/* Unmute button (shown when video is muted and playing) */}
      {muted && videoSrc && !playFailed && (
        <button
          className="absolute top-3 right-14 z-20 flex items-center gap-1.5 bg-black/60 border border-[#1E2D3D] px-2.5 py-1.5 rounded hover:border-[#0EA5E9] transition-colors"
          onClick={handleUnmute}
          title="Unmute"
        >
          <svg className="w-3.5 h-3.5 text-[#4A6278]" fill="currentColor" viewBox="0 0 24 24">
            <path d="M16.5 12c0-1.77-1.02-3.29-2.5-4.03v2.21l2.45 2.45c.03-.2.05-.41.05-.63zm2.5 0c0 .94-.2 1.82-.54 2.64l1.51 1.51C20.63 14.91 21 13.5 21 12c0-4.28-2.99-7.86-7-8.77v2.06c2.89.86 5 3.54 5 6.71zM4.27 3L3 4.27 7.73 9H3v6h4l5 5v-6.73l4.25 4.25c-.67.52-1.42.93-2.25 1.18v2.06c1.38-.31 2.63-.95 3.69-1.81L19.73 21 21 19.73l-9-9L4.27 3zM12 4L9.91 6.09 12 8.18V4z" />
          </svg>
          <span className="font-barlow font-black text-[10px] tracking-[2px] text-[#4A6278] uppercase">Muted</span>
        </button>
      )}

      {/* HUD Corner Brackets */}
      <div className="absolute inset-0 pointer-events-none">
        {/* Top-left */}
        <div className="absolute top-3 left-3 w-6 h-6 border-l-2 border-t-2 border-[#0EA5E9]/60" />
        {/* Top-right */}
        <div className="absolute top-3 right-3 w-6 h-6 border-r-2 border-t-2 border-[#0EA5E9]/60" />
        {/* Bottom-left */}
        <div className="absolute bottom-3 left-3 w-6 h-6 border-l-2 border-b-2 border-[#0EA5E9]/60" />
        {/* Bottom-right */}
        <div className="absolute bottom-3 right-3 w-6 h-6 border-r-2 border-b-2 border-[#0EA5E9]/60" />
      </div>

      {/* Lower Third — Episode Title */}
      {nowPlaying?.title && (
        <div className="absolute bottom-12 left-0 right-0 px-4">
          <div className="bg-[#080B0F]/80 backdrop-blur-sm border border-[#1E2D3D] px-4 py-2 inline-block">
            <p className="font-barlow font-black text-[#C8D6E5] text-sm tracking-[2px] uppercase">
              {nowPlaying.title}
            </p>
          </div>
        </div>
      )}

      {/* Scene Indicator Dots */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-[#0EA5E9]/40"
          />
        ))}
      </div>

      {/* No Video Placeholder */}
      {!videoSrc && (
        <div className="absolute inset-0 flex flex-col items-center justify-center bg-[#080B0F]">
          <div className="w-16 h-16 border-2 border-[#1E2D3D] rounded-full flex items-center justify-center mb-4">
            <div className="w-3 h-3 rounded-full bg-[#0EA5E9] animate-pulse" />
          </div>
          <p className="font-barlow font-black text-[#4A6278] text-sm tracking-[3px] uppercase">
            Awaiting Broadcast
          </p>
          <p className="font-mono text-[#4A6278]/60 text-[10px] mt-2">
            Pipeline is generating first episode...
          </p>
        </div>
      )}
    </div>
  );
}
