"use client";

import { cn } from "@/lib/utils";

type Props = {
  label: string;
  options: readonly string[];
  values: string[];
  onToggle: (value: string) => void;
  className?: string;
};

export function FilterChipGroup({ label, options, values, onToggle, className }: Props) {
  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[12px] font-semibold text-muted">{label}</span>
        {values.length > 0 ? (
          <span className="text-[11px] font-medium text-emerald">{values.length} обрано</span>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {options.map(option => {
          const active = values.includes(option);
          return (
            <button
              key={option}
              type="button"
              onClick={() => onToggle(option)}
              className={cn(
                "rounded-full border px-2.5 py-1.5 text-[12px] font-medium transition-colors",
                active
                  ? "border-emerald bg-emerald text-white"
                  : "border-border bg-white text-ink/80 hover:border-emerald/40 hover:text-ink",
              )}
            >
              {option}
            </button>
          );
        })}
      </div>
    </div>
  );
}
