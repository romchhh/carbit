"use client";

import { useEffect, useId, useRef, useState } from "react";
import { BrandIcon } from "@/components/search/BrandIcon";
import { FilterDropdownPortal } from "@/components/search/FilterDropdownPortal";
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
  getOptionIcon?: (option: string) => string | null | undefined;
  /** Кастомний пошук (UA/RU аліаси тощо). */
  filterOptionsFn?: (options: string[], query: string) => string[];
  /** Підстановка канонічної назви при Enter (напр. «хундай» → Hyundai). */
  resolveQueryFn?: (query: string) => string | null;
  /** Кастомний текст у тригері для multi-select. */
  formatMultiDisplay?: (values: string[]) => string;
  /** Очистити всі обрані (multi). */
  onClearAll?: () => void;
  compact?: boolean;
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
  getOptionIcon,
  filterOptionsFn,
  resolveQueryFn,
  formatMultiDisplay,
  onClearAll,
  compact,
}: Props) {
  const panelId = useId();
  const rootRef = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      const panel = document.getElementById(panelId);
      if (rootRef.current?.contains(target) || panel?.contains(target)) return;
      setOpen(false);
      setQuery("");
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, [panelId]);

  const normalizedQuery = query.trim();
  const filtered = normalizedQuery
    ? (filterOptionsFn ?? ((opts, q) => opts.filter(o => o.toLowerCase().includes(q.trim().toLowerCase()))))(
        options,
        normalizedQuery,
      ).slice(0, 100)
    : options.slice(0, 100);

  const select = (next: string) => {
    if (multiple && onToggle) {
      onToggle(next);
      return;
    }
    onChange(next);
    setOpen(false);
    setQuery("");
  };

  const tryCommitQuery = () => {
    const resolved = resolveQueryFn?.(normalizedQuery);
    if (resolved) {
      select(resolved);
      return;
    }
    if (filtered.length === 1) {
      select(filtered[0]);
    }
  };

  const hasSelection = multiple ? values.length > 0 : Boolean(value?.trim());
  const display = multiple
    ? values.length > 0
      ? formatMultiDisplay?.(values) ?? (values.length <= 2 ? values.join(", ") : `${values.length} обрано`)
      : emptyLabel
    : value;

  const selectedIconUrl =
    !multiple && value && getOptionIcon
      ? getOptionIcon(value)
      : multiple && values.length === 1 && getOptionIcon
        ? getOptionIcon(values[0])
        : null;

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <FilterRow
        label={label}
        value={hasSelection ? display : undefined}
        onClick={() => !disabled && setOpen(v => !v)}
        disabled={disabled}
        compact={compact}
        leading={
          selectedIconUrl ? (
            <BrandIcon src={selectedIconUrl} size={compact ? 18 : 22} className="opacity-90" />
          ) : undefined
        }
      />
      <FilterDropdownPortal open={open && !disabled} anchorRef={rootRef} id={panelId} className="max-h-72">
        {searchable && (
            <div className="border-b border-border/60 p-3">
              <input
                value={query}
                onChange={e => setQuery(e.target.value)}
                onKeyDown={e => {
                  if (e.key === "Enter") {
                    e.preventDefault();
                    tryCommitQuery();
                  }
                }}
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
                    !value || value === emptyLabel
                      ? "font-semibold text-emerald-dark"
                      : "text-muted",
                  )}
                >
                  {emptyLabel}
                </button>
              </li>
            )}
            {multiple && onClearAll && (
              <li>
                <button
                  type="button"
                  onClick={() => {
                    onClearAll();
                    setQuery("");
                    setOpen(false);
                  }}
                  className={cn(
                    "block w-full px-4 py-2.5 text-left text-[14px] transition-colors hover:bg-surface",
                    values.length === 0
                      ? "font-semibold text-emerald-dark"
                      : "text-muted",
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
                const iconUrl = getOptionIcon?.(option);
                return (
                  <li key={option}>
                    <button
                      type="button"
                      onClick={() => select(option)}
                      className={cn(
                        "flex w-full items-center gap-3 px-4 py-2.5 text-left text-[14px] transition-colors hover:bg-surface",
                        active ? "font-semibold text-emerald-dark" : "text-ink",
                      )}
                    >
                      {iconUrl ? (
                        <BrandIcon src={iconUrl} size={22} />
                      ) : (
                        <span className="w-[22px] shrink-0" aria-hidden />
                      )}
                      <span className="min-w-0 flex-1 truncate">{option}</span>
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
            <div className="space-y-2 border-t border-border/60 p-3">
              {values.length > 0 && onClearAll && (
                <button
                  type="button"
                  onClick={() => {
                    onClearAll();
                    setQuery("");
                    setOpen(false);
                  }}
                  className="w-full rounded-full border border-border py-2 text-[13px] font-medium text-muted transition-colors hover:border-ink/20 hover:text-ink"
                >
                  Очистити ({values.length})
                </button>
              )}
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
      </FilterDropdownPortal>
    </div>
  );
}
