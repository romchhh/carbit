"use client";

import { IconMic } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  onClick: () => void;
  className?: string;
  compact?: boolean;
};

export function VoiceSearchTrigger({ onClick, className, compact }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-label="Голосовий пошук"
      className={cn(
        "group relative isolate flex shrink-0 items-center overflow-hidden text-left text-white",
        "bg-gradient-to-br from-[#00C896] via-[#00B4A8] to-[#0891B2]",
        "shadow-[0_10px_30px_-8px_rgba(0,200,150,0.55)] ring-1 ring-white/25",
        "transition-all duration-300 hover:-translate-y-0.5 hover:shadow-[0_16px_40px_-10px_rgba(0,200,150,0.65)]",
        "active:translate-y-0 active:scale-[0.98]",
        compact
          ? "gap-2 rounded-xl px-2.5 py-2 pr-3"
          : "gap-3 rounded-2xl px-3 py-2.5 pr-4",
        className,
      )}
    >
      <span
        aria-hidden
        className={cn(
          "pointer-events-none absolute inset-0 overflow-hidden",
          compact ? "rounded-xl" : "rounded-2xl",
        )}
      >
        <span className="absolute inset-y-0 -left-1/2 w-1/2 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-voice-shimmer" />
      </span>

      <span
        className={cn(
          "relative flex items-center justify-center bg-white/20 shadow-inner backdrop-blur-sm",
          compact ? "h-8 w-8 rounded-lg" : "h-11 w-11 rounded-xl",
        )}
      >
        <span
          className={cn(
            "absolute inset-0 bg-white/10 animate-voice-glow",
            compact ? "rounded-lg" : "rounded-xl",
          )}
        />
        <IconMic size={compact ? 18 : 24} className="relative drop-shadow-sm" />
      </span>

      {compact ? (
        <span className="relative">
          <span className="flex items-center gap-1">
            <span className="text-[12px] font-bold tracking-[-0.01em]">Голосом</span>
            <span className="rounded-full bg-white/20 px-1 py-0.5 text-[8px] font-bold uppercase tracking-wide">
              AI
            </span>
          </span>
        </span>
      ) : (
        <>
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
        </>
      )}
    </button>
  );
}
