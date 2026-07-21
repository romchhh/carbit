"use client";

import { useEffect, useRef, useState } from "react";
import { IconDownload } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import { exportListings, type ExportFormat, type ExportListing } from "@/lib/export-listings";
import { cn } from "@/lib/utils";

const FORMATS: { id: ExportFormat; label: string; hint: string }[] = [
  { id: "excel", label: "Excel", hint: "Рівна таблиця з фото · .xls" },
  { id: "html", label: "HTML-звіт", hint: "Гарна таблиця з фото в браузері" },
  { id: "csv", label: "CSV", hint: "Усі поля · для Google Sheets" },
];

type Props = {
  items: ExportListing[];
  filename?: string;
  className?: string;
  iconSize?: number;
};

export function ExportMenu({ items, filename = "carbit-export", className, iconSize = 13 }: Props) {
  const { user } = useAuth();
  const [open, setOpen] = useState(false);
  const [message, setMessage] = useState("");
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  useEffect(() => {
    if (!message) return;
    const timer = setTimeout(() => setMessage(""), 2500);
    return () => clearTimeout(timer);
  }, [message]);

  const handleExport = (format: ExportFormat) => {
    if (items.length === 0) {
      setMessage("Немає даних для експорту");
      setOpen(false);
      return;
    }
    const ok = exportListings(items, format, filename, user?.preferred_currency);
    if (ok) {
      setMessage(`Завантажено ${items.length} оголошень`);
    }
    setOpen(false);
  };

  return (
    <div ref={ref} className={cn("relative", className)}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex items-center gap-1.5 text-[12px] text-muted transition-colors hover:text-ink"
        aria-expanded={open}
        aria-haspopup="menu"
      >
        <IconDownload size={iconSize} />
        Експорт
      </button>

      {open && (
        <>
          <button
            type="button"
            aria-label="Закрити"
            className="fixed inset-0 z-40 bg-ink/40 sm:hidden"
            onClick={() => setOpen(false)}
          />
          <div
            role="menu"
            className={cn(
              "z-50 overflow-hidden rounded-2xl border border-border/70 bg-white py-1 shadow-card",
              "fixed left-1/2 top-1/2 w-[min(calc(100vw-2rem),16rem)] -translate-x-1/2 -translate-y-1/2",
              "sm:absolute sm:left-auto sm:top-full sm:mt-2 sm:w-64 sm:translate-x-0 sm:translate-y-0 sm:rounded-xl",
              "sm:right-0",
            )}
          >
            <div className="border-b border-border/60 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.08em] text-muted">
              Формат файлу
            </div>
            {FORMATS.map(format => (
              <button
                key={format.id}
                type="button"
                role="menuitem"
                onClick={() => handleExport(format.id)}
                className="block w-full px-3 py-2.5 text-left transition-colors hover:bg-surface active:bg-surface"
              >
                <div className="text-[13px] font-semibold text-ink">{format.label}</div>
                <div className="mt-0.5 text-[11px] text-muted">{format.hint}</div>
              </button>
            ))}
          </div>
        </>
      )}

      {message && (
        <div
          className={cn(
            "z-[60] rounded-lg bg-ink px-3 py-1.5 text-[11px] font-medium text-white shadow-md",
            "fixed bottom-6 left-1/2 max-w-[calc(100vw-2rem)] -translate-x-1/2 whitespace-nowrap",
            "sm:absolute sm:bottom-auto sm:left-auto sm:right-0 sm:top-full sm:mt-2 sm:max-w-none sm:translate-x-0",
          )}
        >
          {message}
        </div>
      )}
    </div>
  );
}
