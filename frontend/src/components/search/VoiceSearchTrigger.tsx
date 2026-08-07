"use client";

import { IconMic } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  onClick: () => void;
  className?: string;
};

export function VoiceSearchTrigger({ onClick, className }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Голосовий пошук"
      className={cn(
        "group relative isolate flex shrink-0 items-center gap-3 overflow-hidden rounded-2xl",
        "bg-gradient-to-br from-[#00C896] via-[#00B4A8] to-[#0891B2]",
        "px-3 py-2.5 pr-4 text-left text-white",
        "shadow-[0_10px_30px_-8px_rgba(0,200,150,0.55)] ring-1 ring-white/25",
        "transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-10px_rgba(0,200,150,0.65)]",
        "active:translate-y-0 active:scale-[0.98]",
        className,
      )}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden rounded-2xl"
      >
        <span className="absolute inset-y-0 -left-1/2 w-1/2 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-voice-shimmer" />
      </span>

      <span className="relative flex h-11 w-11 items-center justify-center rounded-xl bg-white/20 shadow-inner backdrop-blur-sm">
        <span className="absolute inset-0 rounded-xl bg-white/10 animate-voice-glow" />
        <IconMic size={24} className="relative drop-shadow-sm" />
      </span>

      <span className="relative hidden min-w-0 sm:block">
        <span className="flex items-center gap-1.5">
          <span className="text-[14px] font-bold tracking-[-0.01em]">Голосом</span>
          <span className="rounded-full bg-white/20 px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide">
            AI
          </span>
        </span>
        <span className="mt-0.5 block text-[11px] font-medium text-white/80">
          Скажіть, що шукати
        </span>
      </span>

      <span className="relative sm:hidden">
        <span className="block text-[13px] font-bold">Голосом</span>
      </span>
    </button>
  );
}
