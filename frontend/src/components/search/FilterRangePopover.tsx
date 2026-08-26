"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FilterDropdownPortal } from "@/components/search/FilterDropdownPortal";
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
  compact?: boolean;
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
  compact,
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
      const target = e.target as Node;
      const panel = document.getElementById(panelId);
      if (rootRef.current?.contains(target) || panel?.contains(target)) return;
      if (open) close();
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, draftFrom, draftTo, normalize, panelId]);

  const display = displayRange(from, to, suffix);

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <FilterRow label={label} value={display} onClick={() => setOpen(v => !v)} compact={compact} />
      <FilterDropdownPortal open={open} anchorRef={rootRef} id={panelId}>
        <div className="p-4">
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
      </FilterDropdownPortal>
    </div>
  );
}
