"use client";

import { useEffect, useRef, useState } from "react";
import { IconDownload } from "@/components/icons";
import { exportListings, type ExportFormat, type ExportListing } from "@/lib/export-listings";
import { cn } from "@/lib/utils";

const FORMATS: { id: ExportFormat; label: string; hint: string }[] = [
  { id: "csv", label: "CSV", hint: "Таблиця для Excel / Google Sheets" },
  { id: "excel", label: "Excel", hint: "Файл .xls для Microsoft Excel" },
];

type Props = {
  items: ExportListing[];
  filename?: string;
  className?: string;
  iconSize?: number;
};

export function ExportMenu({ items, filename = "carbit-export", className, iconSize = 13 }: Props) {
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
    const ok = exportListings(items, format, filename);
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
        <div className="absolute right-0 top-full z-50 mt-2 w-56 overflow-hidden rounded-xl border border-border/70 bg-white py-1 shadow-card">
          <div className="border-b border-border/60 px-3 py-2 text-[10px] font-bold uppercase tracking-[0.08em] text-muted">
            Формат файлу
          </div>
          {FORMATS.map(format => (
            <button
              key={format.id}
              type="button"
              onClick={() => handleExport(format.id)}
              className="block w-full px-3 py-2.5 text-left transition-colors hover:bg-surface"
            >
              <div className="text-[13px] font-semibold text-ink">{format.label}</div>
              <div className="mt-0.5 text-[11px] text-muted">{format.hint}</div>
            </button>
          ))}
        </div>
      )}

      {message && (
        <div className="absolute right-0 top-full z-40 mt-2 whitespace-nowrap rounded-lg bg-ink px-3 py-1.5 text-[11px] font-medium text-white shadow-md">
          {message}
        </div>
      )}
    </div>
  );
}
