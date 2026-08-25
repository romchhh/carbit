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

export function ColorSwatchPicker({ values, onToggle, metallic, onMetallicChange }: Props) {
  return (
    <div className="space-y-2.5 border-t border-border/60 pt-4">
      <FilterSubsectionLabel
        trailing={
          values.length > 0 ? (
            <span className="text-[11px] font-medium text-emerald">{values.length} обрано</span>
          ) : null
        }
      >
        Колір кузова
      </FilterSubsectionLabel>

      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {COLOR_SWATCHES.map(swatch => {
          const active = values.includes(swatch.name);
          const needsBorder = "border" in swatch && swatch.border;
          return (
            <button
              key={swatch.name}
              type="button"
              onClick={() => onToggle(swatch.name)}
              title={`${swatch.name} (${swatch.hex})`}
              className={cn(
                "flex items-center gap-2 rounded-xl border px-2.5 py-2 text-left transition-all",
                active
                  ? "border-emerald bg-emerald/5 ring-1 ring-emerald/25"
                  : "border-border/70 bg-white hover:border-emerald/35",
              )}
            >
              <span
                className={cn(
                  "h-7 w-7 shrink-0 rounded-full shadow-inner",
                  needsBorder && "border border-border/80",
                  active && "ring-2 ring-emerald ring-offset-1",
                )}
                style={{ backgroundColor: swatch.hex }}
                aria-hidden
              />
              <span className="min-w-0">
                <span className="block truncate text-[12px] font-semibold text-ink">{swatch.name}</span>
                <span className="block font-mono text-[10px] uppercase tracking-wide text-muted">
                  {swatch.hex}
                </span>
              </span>
            </button>
          );
        })}
      </div>

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
            className="h-3.5 w-3.5 rounded-full bg-gradient-to-br from-zinc-200 via-zinc-400 to-zinc-600"
            aria-hidden
          />
          Металік
        </button>
      ) : null}
    </div>
  );
}
