"use client";

import Link from "next/link";
import { IconMic, IconX } from "@/components/icons";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onClose: () => void;
};

const WAVE_HEIGHTS = [0.3, 0.55, 0.85, 1, 0.7, 0.95, 0.5, 0.75, 0.4, 0.65, 0.9, 0.6];

function VoiceWaveform({ active }: { active: boolean }) {
  return (
    <div className="flex h-14 items-end justify-center gap-1.5" aria-hidden>
      {WAVE_HEIGHTS.map((scale, index) => (
        <span
          key={index}
          className={cn(
            "w-1.5 origin-bottom rounded-full bg-gradient-to-t from-emerald to-cyan-400",
            active ? "animate-voice-bar" : "h-2 opacity-30",
          )}
          style={
            active
              ? {
                  animationDelay: `${index * 0.06}s`,
                  height: `${scale * 100}%`,
                }
              : { height: "8px" }
          }
        />
      ))}
    </div>
  );
}

export function VoiceSearchCabinetOnlyOverlay({ open, onClose }: Props) {
  if (!open) return null;

  return (
    <div className="fixed inset-0 z-[120] flex items-end justify-center p-3 sm:items-center sm:p-4">
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-[#0A0C0E]/55 backdrop-blur-md"
        onClick={onClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-cabinet-only-title"
        className="relative z-10 w-full max-w-[420px] animate-voice-pop overflow-hidden rounded-[1.75rem] border border-white/10 bg-white shadow-[0_32px_100px_-20px_rgba(0,0,0,0.45)]"
      >
        <div className="relative overflow-hidden bg-gradient-to-br from-[#0A0C0E] via-[#12201c] to-[#0f2a24] px-5 pb-6 pt-5 text-white">
          <div
            aria-hidden
            className="pointer-events-none absolute -right-8 -top-10 h-36 w-36 rounded-full bg-emerald/30 blur-3xl"
          />
          <div
            aria-hidden
            className="pointer-events-none absolute -bottom-12 -left-6 h-32 w-32 rounded-full bg-cyan-400/20 blur-3xl"
          />

          <div className="relative flex items-start justify-between gap-3">
            <div>
              <div className="mb-2 inline-flex items-center gap-2 rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.12em] text-emerald-light">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald animate-pulse" />
                AI Voice
              </div>
              <p id="voice-cabinet-only-title" className="text-[20px] font-bold tracking-[-0.02em]">
                Голосовий пошук
              </p>
              <p className="mt-1 text-[13px] text-white/70">Доступно після входу в кабінет</p>
            </div>
            <button
              type="button"
              onClick={onClose}
              className="rounded-full bg-white/10 p-2.5 text-white/80 transition-colors hover:bg-white/20 hover:text-white"
              aria-label="Закрити"
            >
              <IconX size={18} />
            </button>
          </div>

          <div className="relative mt-6 flex justify-center">
            <div className="relative flex h-36 w-36 items-center justify-center">
              <span className="absolute inset-5 rounded-full border border-emerald/25 animate-voice-glow" />
              <span
                className="relative z-10 flex h-24 w-24 items-center justify-center rounded-full bg-gradient-to-br from-[#00C896] via-[#00B4A8] to-[#0891B2] text-white shadow-[0_20px_50px_-12px_rgba(0,200,150,0.55)]"
              >
                <IconMic size={40} className="drop-shadow-md" />
              </span>
            </div>
          </div>

          <p className="relative mt-2 text-center text-[12px] font-medium text-white/60">
            Скажіть марку, модель, бюджет і регіон — AI заповнить фільтри
          </p>
        </div>

        <div className="px-5 py-5">
          <div className="rounded-2xl border border-border/70 bg-gradient-to-b from-surface to-white px-4 py-4">
            <VoiceWaveform active={false} />
            <p className="mt-4 min-h-[3.5rem] text-center text-[15px] leading-relaxed text-muted">
              «Toyota Camry, до 18 тисяч доларів, від 2018, Київ»
            </p>
          </div>

          <p className="mt-4 rounded-2xl border border-emerald/20 bg-emerald/10 px-4 py-3.5 text-[13px] leading-relaxed text-emerald-dark">
            Голосовий пошук доступний тільки в кабінеті. Увійдіть або зареєструйтесь, щоб користуватись AI-пошуком.
          </p>

          <div className="mt-4 flex gap-2">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 rounded-full border border-border bg-white py-3 text-[14px] font-semibold text-ink transition-colors hover:bg-surface"
            >
              Зрозуміло
            </button>
            <Link
              href="/auth/login?redirect=/app/search"
              className="flex flex-1 items-center justify-center rounded-full bg-emerald py-3 text-[14px] font-semibold text-white shadow-md shadow-emerald/25 transition-colors hover:bg-emerald-dark"
            >
              У кабінет
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
