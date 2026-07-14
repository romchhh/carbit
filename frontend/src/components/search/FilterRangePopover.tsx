"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FilterRow } from "@/components/search/FilterRow";
import { FormattedNumberInput } from "@/components/search/FormattedNumberInput";
import { cn } from "@/lib/utils";

type CurrencyOption = { value: string; label: string };

type Props = {
  label: string;
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
  format?: (value: string) => string;
  /** Нормалізація при закритті / «Готово» (swap від↔до, clamp). */
  normalize?: (from: string, to: string) => { from: string; to: string };
  hint?: string;
  placeholderFrom?: string;
  placeholderTo?: string;
  suffix?: string;
  currency?: string;
  currencyOptions?: CurrencyOption[];
  onCurrencyChange?: (currency: string) => void;
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
  normalize,
  hint,
  placeholderFrom,
  placeholderTo,
  suffix,
  currency,
  currencyOptions,
  onCurrencyChange,
  className,
}: Props) {
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [draftFrom, setDraftFrom] = useState(from);
  const [draftTo, setDraftTo] = useState(to);

  useEffect(() => {
    if (!open) {
      setDraftFrom(from);
      setDraftTo(to);
    }
  }, [from, to, open]);

  const commit = (nextFrom = draftFrom, nextTo = draftTo) => {
    const normalized = normalize
      ? normalize(nextFrom, nextTo)
      : { from: nextFrom, to: nextTo };
    onChange(normalized.from, normalized.to);
    setDraftFrom(normalized.from);
    setDraftTo(normalized.to);
    return normalized;
  };

  const close = () => {
    commit();
    setOpen(false);
  };

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        if (open) close();
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, draftFrom, draftTo, normalize]);

  const display = displayRange(from, to, suffix);

  return (
    <div ref={rootRef} className={cn("relative", open && "z-[80]", className)}>
      <FilterRow label={label} value={display} onClick={() => setOpen(v => !v)} />
      {open && (
        <div
          id={panelId}
          className="absolute left-0 right-0 top-[calc(100%+6px)] z-[90] rounded-xl border border-border bg-white p-4 shadow-card"
        >
          <div className="mb-3 flex items-center justify-between gap-2">
            <div className="text-[12px] font-semibold text-ink">{label}</div>
            {currencyOptions && onCurrencyChange && (
              <div className="flex rounded-full border border-border bg-surface p-0.5">
                {currencyOptions.map(option => (
                  <button
                    key={option.value}
                    type="button"
                    onClick={() => onCurrencyChange(option.value)}
                    className={cn(
                      "rounded-full px-2.5 py-1 text-[11px] font-semibold transition-colors",
                      currency === option.value
                        ? "bg-white text-ink shadow-sm"
                        : "text-muted hover:text-ink",
                    )}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <div className="flex items-center gap-2">
            <FormattedNumberInput
              value={draftFrom}
              onChange={setDraftFrom}
              format={format}
              placeholder={placeholderFrom}
              className="input-field"
              autoFocus
            />
            <span className="text-[12px] text-muted">—</span>
            <FormattedNumberInput
              value={draftTo}
              onChange={setDraftTo}
              format={format}
              placeholder={placeholderTo}
              className="input-field"
            />
          </div>
          {hint && (
            <p className="mt-2 text-[11px] leading-snug text-muted">{hint}</p>
          )}
          <button
            type="button"
            onClick={close}
            className="mt-3 w-full rounded-full bg-emerald py-2 text-[13px] font-semibold text-white hover:bg-emerald-dark transition-colors"
          >
            Готово
          </button>
        </div>
      )}
    </div>
  );
}
