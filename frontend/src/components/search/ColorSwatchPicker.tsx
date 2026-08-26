"use client";

import { FilterSubsectionLabel } from "@/components/search/FilterSubsectionLabel";
import { COLOR_SWATCHES } from "@/lib/search-catalog";
import { cn } from "@/lib/utils";

type Props = {
  values: string[];
  onToggle: (name: string) => void;
  metallic?: boolean;
  onMetallicChange?: (value: boolean) => void;
};

function CheckIcon({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 16 16" className={className} aria-hidden>
      <path
        d="M3.5 8.2 6.4 11l6.1-6.3"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

function isLightColor(hex: string): boolean {
  const normalized = hex.replace("#", "");
  if (normalized.length !== 6) return false;
  const r = parseInt(normalized.slice(0, 2), 16);
  const g = parseInt(normalized.slice(2, 4), 16);
  const b = parseInt(normalized.slice(4, 6), 16);
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.72;
}

export function ColorSwatchPicker({ values, onToggle, metallic, onMetallicChange }: Props) {
  return (
    <div className="space-y-3 border-t border-border/60 pt-4">
      <FilterSubsectionLabel
        trailing={
          values.length > 0 ? (
            <span className="text-[11px] font-medium text-emerald">{values.length} обрано</span>
          ) : null
        }
      >
        Колір кузова
      </FilterSubsectionLabel>

      <div className="grid grid-cols-6 gap-x-2 gap-y-3 sm:grid-cols-6">
        {COLOR_SWATCHES.map(swatch => {
          const active = values.includes(swatch.name);
          const needsBorder = "border" in swatch && swatch.border;
          const light = needsBorder || isLightColor(swatch.hex);
          return (
            <button
              key={swatch.name}
              type="button"
              onClick={() => onToggle(swatch.name)}
              title={swatch.name}
              aria-label={swatch.name}
              aria-pressed={active}
              className="group flex flex-col items-center gap-1.5 rounded-lg p-0.5 transition-transform active:scale-95"
            >
              <span
                className={cn(
                  "relative flex h-9 w-9 items-center justify-center rounded-full transition-all",
                  "shadow-[inset_0_1px_2px_rgba(0,0,0,0.12)]",
                  needsBorder && "ring-1 ring-inset ring-black/10",
                  active
                    ? "ring-2 ring-emerald ring-offset-2 ring-offset-white"
                    : "group-hover:ring-2 group-hover:ring-emerald/30 group-hover:ring-offset-1 group-hover:ring-offset-white",
                )}
                style={{ backgroundColor: swatch.hex }}
              >
                {active ? (
                  <CheckIcon
                    className={cn(
                      "h-4 w-4 drop-shadow-sm",
                      light ? "text-emerald-dark" : "text-white",
                    )}
                  />
                ) : null}
              </span>
              <span
                className={cn(
                  "max-w-[52px] truncate text-center text-[10px] leading-tight",
                  active ? "font-semibold text-ink" : "font-medium text-muted",
                )}
              >
                {swatch.name}
              </span>
            </button>
          );
        })}
      </div>

      {values.length > 0 ? (
        <div className="flex flex-wrap gap-1.5">
          {values.map(color => {
            const swatch = COLOR_SWATCHES.find(item => item.name === color);
            return (
              <button
                key={color}
                type="button"
                onClick={() => onToggle(color)}
                className="inline-flex items-center gap-1.5 rounded-full border border-emerald/25 bg-emerald/5 px-2.5 py-1 text-[11px] font-medium text-emerald-dark"
              >
                {swatch ? (
                  <span
                    className={cn(
                      "h-3 w-3 rounded-full",
                      "border" in swatch && swatch.border && "border border-border/70",
                    )}
                    style={{ backgroundColor: swatch.hex }}
                    aria-hidden
                  />
                ) : null}
                {color}
                <span aria-hidden className="text-[10px] opacity-70">
                  ×
                </span>
              </button>
            );
          })}
        </div>
      ) : null}

      {onMetallicChange ? (
        <button
          type="button"
          onClick={() => onMetallicChange(!metallic)}
          className={cn(
            "inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[12px] font-medium transition-colors",
            metallic
              ? "border-emerald bg-emerald text-white"
              : "border-border bg-white text-muted hover:border-emerald/40 hover:text-ink",
          )}
        >
          <span
            className="h-3.5 w-3.5 rounded-full bg-gradient-to-br from-zinc-200 via-zinc-400 to-zinc-600 shadow-inner"
            aria-hidden
          />
          Металік
        </button>
      ) : null}
    </div>
  );
}
