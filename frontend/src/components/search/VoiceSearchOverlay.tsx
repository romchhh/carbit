"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { IconMic, IconX } from "@/components/icons";
import { useVoiceSearch } from "@/hooks/useVoiceSearch";
import type { AiParseSearchResult } from "@/lib/api";
import {
  VOICE_SEARCH_EXAMPLES,
  buildVoiceFilterChips,
  isMarketDiscoveryResult,
} from "@/lib/voice-search-summary";

type Props = {
  open: boolean;
  onClose: () => void;
  onApplied: (raw: Record<string, unknown>, result: AiParseSearchResult, searchNow?: boolean) => void;
};

const WAVE_HEIGHTS = [0.3, 0.55, 0.85, 1, 0.7, 0.95, 0.5, 0.75, 0.4, 0.65, 0.9, 0.6];

function VoiceWaveform({ active, large }: { active: boolean; large?: boolean }) {
  return (
    <div
      className={cn("flex items-end justify-center gap-1", large ? "h-14 gap-1.5" : "h-10 gap-1")}
      aria-hidden
    >
      {WAVE_HEIGHTS.map((scale, index) => (
        <span
          key={index}
          className={cn(
            "origin-bottom rounded-full bg-gradient-to-t from-emerald to-cyan-400",
            large ? "w-1.5" : "w-1",
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

function VoiceOrb({
  listening,
  processing,
  onClick,
  disabled,
}: {
  listening: boolean;
  processing: boolean;
  onClick: () => void;
  disabled: boolean;
}) {
  return (
    <div className="relative flex h-36 w-36 items-center justify-center">
      {(listening || processing) && (
        <>
          <span
            className={cn(
              "absolute inset-2 rounded-full border-2",
              listening ? "border-red-400/40 animate-ping" : "border-emerald/30 animate-voice-glow",
            )}
          />
          <span
            className={cn(
              "absolute inset-5 rounded-full border",
              listening ? "border-red-300/30" : "border-emerald/25 animate-voice-glow",
            )}
            style={{ animationDelay: "0.4s" }}
          />
        </>
      )}

      <button
        type="button"
        onClick={onClick}
        disabled={disabled}
        aria-label={listening ? "Зупинити запис" : processing ? "Обробка" : "Почати запис"}
        className={cn(
          "relative z-10 flex h-24 w-24 items-center justify-center rounded-full text-white transition-all duration-300",
          "shadow-[0_20px_50px_-12px_rgba(0,200,150,0.55)]",
          listening
            ? "bg-gradient-to-br from-red-500 to-rose-600 shadow-[0_20px_50px_-12px_rgba(239,68,68,0.5)]"
            : "bg-gradient-to-br from-[#00C896] via-[#00B4A8] to-[#0891B2] hover:scale-[1.03]",
          disabled && "cursor-wait opacity-70",
        )}
      >
        {listening && (
          <span className="absolute inset-0 animate-ping rounded-full bg-red-400/25" />
        )}
        <IconMic size={40} className="relative drop-shadow-md" />
      </button>
    </div>
  );
}

function FilterChips({
  raw,
  marketDiscovery,
}: {
  raw: Record<string, unknown>;
  marketDiscovery?: boolean;
}) {
  const chips = buildVoiceFilterChips(raw, { marketDiscovery });
  if (!chips.length) {
    return (
      <p className="text-center text-[13px] text-muted">
        Не вдалося виділити параметри — перевірте фільтри вручну.
      </p>
    );
  }

  return (
    <div className="flex flex-wrap justify-center gap-2">
      {chips.map(chip => (
        <span
          key={chip.key}
          className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-emerald/25 bg-emerald/10 px-3 py-1.5 text-[12px] text-emerald-dark"
        >
          <span className="font-semibold text-emerald/80">{chip.label}:</span>
          <span className="truncate font-medium text-ink">{chip.value}</span>
        </span>
      ))}
    </div>
  );
}

export function VoiceSearchOverlay({ open, onClose, onApplied }: Props) {
  const { phase, transcript, message, result, start, finishRecording, reset, isActive } =
    useVoiceSearch();
  const startedRef = useRef(false);

  useEffect(() => {
    if (!open) {
      startedRef.current = false;
      reset();
      return;
    }
    if (startedRef.current) return;
    startedRef.current = true;
    void start();
  }, [open, reset, start]);

  const handleMicClick = () => {
    if (phase === "listening") {
      void finishRecording();
      return;
    }
    if (phase === "error" || phase === "done") {
      void start();
    }
  };

  const handleClose = () => {
    if (isActive) void finishRecording();
    reset();
    onClose();
  };

  const handleApply = (searchNow = false) => {
    if (!result?.understood || !result.filters) return;
    onApplied(result.filters, result, searchNow);
    reset();
    onClose();
  };

  if (!open) return null;

  const listening = phase === "listening";
  const processing = phase === "processing";
  const review = phase === "done";
  const failed = phase === "error";
  const marketDiscovery = Boolean(result && isMarketDiscoveryResult(result));

  const statusLabel = listening
    ? "Слухаю…"
    : processing
      ? "AI розбирає запит"
      : review
        ? marketDiscovery
          ? "Підбираю варіанти по ринку"
          : "Перевірте, що зрозумів AI"
        : failed
          ? "Не зрозумів"
          : "Готовий до запису";

  return (
    <div className="fixed inset-0 z-[120] flex items-end justify-center p-3 sm:items-center sm:p-4">
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-[#0A0C0E]/55 backdrop-blur-md"
        onClick={handleClose}
      />

      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="voice-search-title"
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
              <p id="voice-search-title" className="text-[20px] font-bold tracking-[-0.02em]">
                Голосовий пошук
              </p>
              <p className="mt-1 text-[13px] text-white/70">{statusLabel}</p>
            </div>
            <button
              type="button"
              onClick={handleClose}
              className="rounded-full bg-white/10 p-2.5 text-white/80 transition-colors hover:bg-white/20 hover:text-white"
              aria-label="Закрити"
            >
              <IconX size={18} />
            </button>
          </div>

          {!review && (
            <>
              <div className="relative mt-6 flex justify-center">
                <VoiceOrb
                  listening={listening}
                  processing={processing}
                  onClick={handleMicClick}
                  disabled={processing}
                />
              </div>

              <p className="relative mt-2 text-center text-[12px] font-medium text-white/60">
                {listening
                  ? "«Готово» — одразу до пошуку · або 5 сек тиші"
                  : failed
                    ? "Натисніть мікрофон і спробуйте ще раз"
                    : processing
                      ? "Розбираю марку, ціну, рік, регіон…"
                      : "Скажіть бюджет, рік або марку — AI знайде по ринку"}
              </p>
            </>
          )}
        </div>

        <div className="px-5 py-5">
          {listening && (
            <button
              type="button"
              onClick={() => void finishRecording()}
              className="mb-4 flex w-full items-center justify-center gap-2 rounded-full bg-emerald py-3.5 text-[15px] font-semibold text-white shadow-lg shadow-emerald/30 transition-transform hover:scale-[1.01] active:scale-[0.99]"
            >
              Готово — аналізувати
            </button>
          )}

          {review && result?.filters ? (
            <div className="space-y-4">
              <div className="rounded-2xl border border-border/70 bg-gradient-to-b from-surface to-white px-4 py-4">
                <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-wide text-muted">
                  Ви сказали
                </p>
                <p className="text-center text-[14px] leading-relaxed text-ink">
                  «{result.transcript || transcript}»
                </p>
              </div>

              <div className="rounded-2xl border border-emerald/20 bg-emerald/5 px-4 py-4">
                <p className="mb-3 text-center text-[11px] font-semibold uppercase tracking-wide text-emerald-dark">
                  AI зрозумів
                </p>
                <FilterChips raw={result.filters} marketDiscovery={marketDiscovery} />
              </div>

              {message && (
                <p className="rounded-2xl border border-emerald/20 bg-emerald/10 px-4 py-3 text-[13px] leading-relaxed text-emerald-dark">
                  {message}
                </p>
              )}

              {marketDiscovery ? (
                <>
                  <button
                    type="button"
                    onClick={() => handleApply(true)}
                    className="flex w-full items-center justify-center rounded-full bg-ink py-3.5 text-[15px] font-semibold text-white shadow-md transition-transform hover:scale-[1.01] active:scale-[0.99]"
                  >
                    Шукати по ринку
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApply(false)}
                    className="w-full py-2 text-[13px] font-medium text-muted transition-colors hover:text-ink"
                  >
                    Лише застосувати фільтри
                  </button>
                </>
              ) : (
                <div className="grid grid-cols-2 gap-2">
                  <button
                    type="button"
                    onClick={() => handleApply(false)}
                    className="rounded-full border border-border bg-white py-3 text-[14px] font-semibold text-ink transition-colors hover:bg-surface"
                  >
                    Застосувати
                  </button>
                  <button
                    type="button"
                    onClick={() => handleApply(true)}
                    className="rounded-full bg-ink py-3 text-[14px] font-semibold text-white shadow-md transition-transform hover:scale-[1.01] active:scale-[0.99]"
                  >
                    Шукати зараз
                  </button>
                </div>
              )}

              <button
                type="button"
                onClick={() => void start()}
                className="w-full py-2 text-[13px] font-medium text-muted transition-colors hover:text-ink"
              >
                Сказати інакше
              </button>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-border/70 bg-gradient-to-b from-surface to-white px-4 py-4">
                {processing ? (
                  <div className="flex flex-col items-center justify-center gap-3 py-3">
                    <VoiceWaveform active large />
                    <p className="text-[13px] font-semibold text-ink/70">AI аналізує запит…</p>
                  </div>
                ) : (
                  <>
                    <VoiceWaveform active={listening} large />
                    <p
                      className={cn(
                        "mt-4 min-h-[3.5rem] text-center text-[15px] leading-relaxed",
                        transcript ? "font-medium text-ink" : "text-muted",
                      )}
                    >
                      {transcript ||
                        (listening
                          ? "Говоріть природно — AI розбере марку, ціну, рік і регіон"
                          : "Тут з’явиться те, що ви скажете")}
                    </p>
                  </>
                )}
              </div>

              {listening && (
                <div className="mt-4">
                  <p className="mb-2 text-center text-[11px] font-medium text-muted">Приклади</p>
                  <div className="flex flex-col gap-1.5">
                    {VOICE_SEARCH_EXAMPLES.map(example => (
                      <p
                        key={example}
                        className="rounded-xl bg-surface/80 px-3 py-2 text-center text-[11px] leading-relaxed text-muted"
                      >
                        «{example}»
                      </p>
                    ))}
                  </div>
                </div>
              )}

              {message && (
                <p
                  className={cn(
                    "mt-4 rounded-2xl px-4 py-3.5 text-[13px] leading-relaxed",
                    failed
                      ? "border border-red-100 bg-red-50 text-red-700"
                      : "border border-emerald/20 bg-emerald/10 text-emerald-dark",
                  )}
                >
                  {message}
                </p>
              )}

              {failed && (
                <button
                  type="button"
                  onClick={() => void start()}
                  className="mt-4 flex w-full items-center justify-center gap-2 rounded-full border border-border py-3 text-[14px] font-semibold text-ink transition-colors hover:bg-surface"
                >
                  <IconMic size={18} />
                  Спробувати ще
                </button>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
