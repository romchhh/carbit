"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FilterRow } from "@/components/search/FilterRow";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
  format?: (value: string) => string;
  placeholderFrom?: string;
  placeholderTo?: string;
  suffix?: string;
  className?: string;
};

function displayRange(from: string, to: string, suffix = ""): string {
  if (from && to) return `${from} — ${to}${suffix ? ` ${suffix}` : ""}`;
  if (from) return `від ${from}${suffix ? ` ${suffix}` : ""}`;
  if (to) return `до ${to}${suffix ? ` ${suffix}` : ""}`;
  return "";
}

export function FilterRangePopover({
  label,
  from,
  to,
  onChange,
  format,
  placeholderFrom,
  placeholderTo,
  suffix,
  className,
}: Props) {
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const handleFrom = (value: string) => {
    onChange(format ? format(value) : value, to);
  };

  const handleTo = (value: string) => {
    onChange(from, format ? format(value) : value);
  };

  const display = displayRange(from, to, suffix);

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <FilterRow label={label} value={display} onClick={() => setOpen(v => !v)} />
      {open && (
        <div
          id={panelId}
          className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 rounded-xl border border-border bg-white p-4 shadow-card"
        >
          <div className="mb-3 text-[12px] font-semibold text-ink">{label}</div>
          <div className="flex items-center gap-2">
            <input
              value={from}
              onChange={e => handleFrom(e.target.value)}
              placeholder={placeholderFrom}
              className="input-field"
              inputMode="numeric"
              autoFocus
            />
            <span className="text-[12px] text-muted">—</span>
            <input
              value={to}
              onChange={e => handleTo(e.target.value)}
              placeholder={placeholderTo}
              className="input-field"
              inputMode="numeric"
            />
          </div>
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="mt-3 w-full rounded-full bg-emerald py-2 text-[13px] font-semibold text-white hover:bg-emerald-dark transition-colors"
          >
            Готово
          </button>
        </div>
      )}
    </div>
  );
}
