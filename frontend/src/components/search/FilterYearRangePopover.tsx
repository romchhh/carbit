"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FilterDropdownPortal } from "@/components/search/FilterDropdownPortal";
import { FilterRow } from "@/components/search/FilterRow";
import { normalizeYearRange, yearFilterOptions } from "@/lib/search-catalog";
import { cn } from "@/lib/utils";

type Props = {
  label?: string;
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
  className?: string;
  compact?: boolean;
};

function displayRange(from: string, to: string): string {
  if (from && to) return `${from} — ${to}`;
  if (from) return `від ${from}`;
  if (to) return `до ${to}`;
  return "";
}

const YEAR_OPTIONS = yearFilterOptions();

export function FilterYearRangePopover({
  label = "Рік випуску",
  from,
  to,
  onChange,
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
    const normalized = normalizeYearRange(nextFrom, nextTo);
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
  }, [open, draftFrom, draftTo, panelId]);

  const display = displayRange(from, to);

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <FilterRow label={label} value={display} onClick={() => setOpen(v => !v)} compact={compact} />
      <FilterDropdownPortal open={open} anchorRef={rootRef} id={panelId}>
        <div className="p-4">
          <div className="mb-3 text-[12px] font-semibold text-ink">{label}</div>
          <div className="flex items-center gap-2">
            <select
              value={draftFrom}
              onChange={e => setDraftFrom(e.target.value)}
              className="input-field min-w-0 flex-1"
              aria-label="Рік від"
            >
              <option value="">Від</option>
              {YEAR_OPTIONS.map(year => (
                <option key={`from-${year}`} value={String(year)}>
                  {year}
                </option>
              ))}
            </select>
            <span className="text-[12px] text-muted">—</span>
            <select
              value={draftTo}
              onChange={e => setDraftTo(e.target.value)}
              className="input-field min-w-0 flex-1"
              aria-label="Рік до"
            >
              <option value="">До</option>
              {YEAR_OPTIONS.map(year => (
                <option key={`to-${year}`} value={String(year)}>
                  {year}
                </option>
              ))}
            </select>
          </div>
          <button
            type="button"
            onClick={close}
            className="mt-3 w-full rounded-full bg-emerald py-2 text-[13px] font-semibold text-white transition-colors hover:bg-emerald-dark"
          >
            Готово
          </button>
        </div>
      </FilterDropdownPortal>
    </div>
  );
}
