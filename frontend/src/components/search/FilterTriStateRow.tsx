"use client";

import { cn } from "@/lib/utils";

export type TriFilterValue = "" | "show" | "hide";

const OPTIONS: { value: TriFilterValue; label: string }[] = [
  { value: "", label: "Всі" },
  { value: "show", label: "Показати" },
  { value: "hide", label: "Сховати" },
];

type Props = {
  label: string;
  value: TriFilterValue;
  onChange: (value: TriFilterValue) => void;
};

export function FilterTriStateRow({ label, value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-[13px] font-medium text-ink">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {OPTIONS.map(opt => {
          const active = value === opt.value;
          return (
            <button
              key={opt.label}
              type="button"
              onClick={() => onChange(opt.value)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
                active
                  ? "border-emerald bg-emerald text-white"
                  : "border-border bg-white text-muted hover:border-emerald/40",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

type SegmentedProps<T extends string> = {
  label: string;
  value: T;
  options: ReadonlyArray<{ value: T; label: string }>;
  onChange: (value: T) => void;
};

export function FilterSegmentedRow<T extends string>({
  label,
  value,
  options,
  onChange,
}: SegmentedProps<T>) {
  return (
    <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
      <span className="text-[13px] font-medium text-ink">{label}</span>
      <div className="flex flex-wrap gap-1.5">
        {options.map(opt => {
          const active = value === opt.value;
          return (
            <button
              key={opt.value || "all"}
              type="button"
              onClick={() => onChange(opt.value)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
                active
                  ? "border-emerald bg-emerald text-white"
                  : "border-border bg-white text-muted hover:border-emerald/40",
              )}
            >
              {opt.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

type BoolProps = {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
};

export function FilterBooleanRow({ label, checked, onChange }: BoolProps) {
  return (
    <label className="flex cursor-pointer items-center justify-between gap-3 py-0.5">
      <span className="text-[13px] font-medium text-ink">{label}</span>
      <input
        type="checkbox"
        checked={checked}
        onChange={e => onChange(e.target.checked)}
        className="h-4 w-4 rounded border-border text-emerald focus:ring-emerald/30"
      />
    </label>
  );
}
