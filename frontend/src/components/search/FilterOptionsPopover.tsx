"use client";

import { useEffect, useId, useRef, useState } from "react";
import { FilterRow } from "@/components/search/FilterRow";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  value: string;
  values?: string[];
  options: string[];
  onChange: (value: string) => void;
  onToggle?: (value: string) => void;
  multiple?: boolean;
  searchable?: boolean;
  disabled?: boolean;
  emptyLabel?: string;
  className?: string;
};

export function FilterOptionsPopover({
  label,
  value,
  values = [],
  options,
  onChange,
  onToggle,
  multiple = false,
  searchable = false,
  disabled = false,
  emptyLabel = "Будь-яка",
  className,
}: Props) {
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
        setQuery("");
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  const normalizedQuery = query.trim().toLowerCase();
  const filtered = normalizedQuery
    ? options.filter(o => o.toLowerCase().includes(normalizedQuery)).slice(0, 100)
    : options.slice(0, 100);

  const display = multiple
    ? values.length > 0
      ? values.join(", ")
      : ""
    : value;

  const select = (next: string) => {
    if (multiple && onToggle) {
      onToggle(next);
      return;
    }
    onChange(next);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <FilterRow
        label={label}
        value={display}
        onClick={() => !disabled && setOpen(v => !v)}
        disabled={disabled}
      />
      {open && !disabled && (
        <div
          id={panelId}
          className="absolute left-0 right-0 top-[calc(100%+6px)] z-50 max-h-72 overflow-hidden rounded-xl border border-border bg-white shadow-card"
        >
          {searchable && (
            <div className="border-b border-border/60 p-3">
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                placeholder="Пошук..."
                className="input-field"
                autoFocus
              />
            </div>
          )}
          <ul className="max-h-56 overflow-y-auto py-1">
            {!multiple && (
              <li>
                <button
                  type="button"
                  onClick={() => select("")}
                  className={cn(
                    "block w-full px-4 py-2.5 text-left text-[14px] transition-colors hover:bg-surface",
                    !value ? "font-semibold text-emerald-dark" : "text-muted",
                  )}
                >
                  {emptyLabel}
                </button>
              </li>
            )}
            {filtered.length === 0 ? (
              <li className="px-4 py-3 text-[13px] text-muted">Нічого не знайдено</li>
            ) : (
              filtered.map(option => {
                const active = multiple ? values.includes(option) : value === option;
                return (
                  <li key={option}>
                    <button
                      type="button"
                      onClick={() => select(option)}
                      className={cn(
                        "flex w-full items-center justify-between px-4 py-2.5 text-left text-[14px] transition-colors hover:bg-surface",
                        active ? "font-semibold text-emerald-dark" : "text-ink",
                      )}
                    >
                      <span>{option}</span>
                      {multiple && active && (
                        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden>
                          <path d="M3 7l3 3 5-6" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                        </svg>
                      )}
                    </button>
                  </li>
                );
              })
            )}
          </ul>
          {multiple && (
            <div className="border-t border-border/60 p-3">
              <button
                type="button"
                onClick={() => {
                  setOpen(false);
                  setQuery("");
                }}
                className="w-full rounded-full bg-emerald py-2 text-[13px] font-semibold text-white hover:bg-emerald-dark transition-colors"
              >
                Готово
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
