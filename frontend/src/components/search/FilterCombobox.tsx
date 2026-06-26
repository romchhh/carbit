"use client";

import { useEffect, useId, useRef, useState } from "react";
import { cn } from "@/lib/utils";

type Props = {
  value: string;
  onChange: (value: string) => void;
  options: string[];
  placeholder?: string;
  emptyLabel?: string;
  disabled?: boolean;
  className?: string;
};

export function FilterCombobox({
  value,
  onChange,
  options,
  placeholder = "Пошук...",
  emptyLabel = "Будь-яка",
  disabled = false,
  className,
}: Props) {
  const listId = useId();
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

  const displayValue = open ? query : value;

  const select = (next: string) => {
    onChange(next);
    setOpen(false);
    setQuery("");
  };

  return (
    <div ref={rootRef} className={cn("relative", className)}>
      <div className="relative">
        <input
          type="text"
          value={displayValue}
          disabled={disabled}
          placeholder={value ? value : placeholder}
          onFocus={() => !disabled && setOpen(true)}
          onChange={e => {
            setQuery(e.target.value);
            setOpen(true);
          }}
          className={cn(
            "input-field w-full pr-7",
            disabled && "cursor-not-allowed opacity-50",
          )}
          aria-expanded={open}
          aria-controls={listId}
          autoComplete="off"
        />
        {(value || query) && !disabled && (
          <button
            type="button"
            onClick={() => select("")}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-[11px] text-muted hover:text-ink"
            aria-label="Очистити"
          >
            ✕
          </button>
        )}
      </div>

      {open && !disabled && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 mt-1 max-h-52 w-full overflow-y-auto rounded-xl border border-border bg-white py-1 shadow-card"
        >
          <li>
            <button
              type="button"
              onClick={() => select("")}
              className={cn(
                "block w-full px-3 py-2 text-left text-[12px] transition-colors hover:bg-surface",
                !value ? "font-semibold text-emerald-dark" : "text-muted",
              )}
            >
              {emptyLabel}
            </button>
          </li>
          {filtered.length === 0 ? (
            <li className="px-3 py-2 text-[12px] text-muted">Нічого не знайдено</li>
          ) : (
            filtered.map(option => (
              <li key={option}>
                <button
                  type="button"
                  onClick={() => select(option)}
                  className={cn(
                    "block w-full px-3 py-2 text-left text-[12px] transition-colors hover:bg-surface",
                    value === option ? "font-semibold text-ink" : "text-ink",
                  )}
                >
                  {option}
                </button>
              </li>
            ))
          )}
          {options.length > 100 && !normalizedQuery && (
            <li className="border-t border-border/60 px-3 py-2 text-[10px] text-muted">
              Почніть вводити для пошуку серед {options.length} варіантів
            </li>
          )}
        </ul>
      )}
    </div>
  );
}
