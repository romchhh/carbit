"use client";

import Image from "next/image";
import { useCallback, useEffect, useState } from "react";
import { ListingDetailModal } from "@/components/listings/ListingDetailModal";
import { adminApi, type AdminListingRow } from "@/lib/admin-api";
import { formatKyivDateTime } from "@/lib/datetime";
import type { Listing } from "@/types/api";

const SOURCE_OPTIONS = [
  { value: "", label: "Усі джерела" },
  { value: "auto_ria", label: "AUTO.RIA" },
  { value: "olx", label: "OLX" },
  { value: "imperiya", label: "Імперія Авто" },
  { value: "car_market", label: "Car Market" },
  { value: "reono", label: "REONO" },
  { value: "udrive", label: "uDrive" },
  { value: "telegram", label: "Telegram" },
];

const SOURCE_LABELS: Record<string, string> = {
  auto_ria: "AUTO.RIA",
  olx: "OLX",
  imperiya: "Імперія Авто",
  car_market: "Car Market",
  reono: "REONO",
  udrive: "uDrive",
  telegram: "Telegram",
};

export default function AdminListingsPage() {
  const [items, setItems] = useState<AdminListingRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [source, setSource] = useState("");
  const [search, setSearch] = useState("");
  const [query, setQuery] = useState("");
  const [duplicatesOnly, setDuplicatesOnly] = useState(false);
  const [loading, setLoading] = useState(true);
  const [selectedListing, setSelectedListing] = useState<Listing | null>(null);
  const [detailLoadingId, setDetailLoadingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.listingsBrowse(page, {
        source: source || undefined,
        search: query || undefined,
        duplicates_only: duplicatesOnly,
      });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [page, source, query, duplicatesOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / 30));

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    setQuery(search);
  };

  const openListing = async (id: string) => {
    setDetailLoadingId(id);
    try {
      const listing = await adminApi.listing(id);
      setSelectedListing(listing);
    } finally {
      setDetailLoadingId(null);
    }
  };

  return (
    <div className="max-w-[1200px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Оголошення</h1>
      <p className="text-[13px] text-muted mb-6">
        База зібраних оголошень · всього {total.toLocaleString("uk-UA")}
      </p>

      <div className="mb-6 flex flex-wrap items-end gap-3">
        <form onSubmit={handleSearch} className="flex flex-1 min-w-[200px] gap-2">
          <input
            type="search"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Пошук за назвою, маркою, моделлю…"
            className="flex-1 rounded-lg border border-border px-3 py-2 text-[13px]"
          />
          <button type="submit" className="rounded-lg bg-ink px-4 py-2 text-[13px] font-semibold text-white">
            Знайти
          </button>
        </form>
        <select
          value={source}
          onChange={e => { setSource(e.target.value); setPage(1); }}
          className="rounded-lg border border-border px-3 py-2 text-[13px]"
        >
          {SOURCE_OPTIONS.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <label className="flex items-center gap-2 text-[13px]">
          <input
            type="checkbox"
            checked={duplicatesOnly}
            onChange={e => { setDuplicatesOnly(e.target.checked); setPage(1); }}
          />
          Лише дублі
        </label>
      </div>

      <div className="rounded-2xl border border-border bg-white overflow-hidden">
        {loading ? (
          <div className="flex justify-center py-16">
            <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
          </div>
        ) : items.length === 0 ? (
          <p className="py-16 text-center text-[13px] text-muted">Нічого не знайдено</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[13px]">
              <thead className="border-b border-border bg-surface/50 text-[11px] uppercase tracking-wide text-muted">
                <tr>
                  <th className="px-4 py-3 font-semibold w-[72px]" />
                  <th className="px-4 py-3 font-semibold">Оголошення</th>
                  <th className="px-4 py-3 font-semibold">Джерело</th>
                  <th className="px-4 py-3 font-semibold">Ціна</th>
                  <th className="px-4 py-3 font-semibold">Регіон</th>
                  <th className="px-4 py-3 font-semibold">Знайдено</th>
                  <th className="px-4 py-3 font-semibold" />
                </tr>
              </thead>
              <tbody>
                {items.map(item => (
                  <tr
                    key={item.id}
                    role="button"
                    tabIndex={0}
                    onClick={() => void openListing(item.id)}
                    onKeyDown={e => {
                      if (e.key === "Enter" || e.key === " ") {
                        e.preventDefault();
                        void openListing(item.id);
                      }
                    }}
                    className="border-b border-border/60 hover:bg-surface/30 cursor-pointer focus:outline-none focus-visible:bg-surface/40"
                  >
                    <td className="px-4 py-3">
                      <div className="relative h-12 w-16 overflow-hidden rounded-lg bg-surface">
                        {item.image ? (
                          <Image
                            src={item.image}
                            alt=""
                            fill
                            className="object-cover"
                            sizes="64px"
                            unoptimized
                          />
                        ) : (
                          <div className="flex h-full items-center justify-center text-[9px] text-muted">
                            —
                          </div>
                        )}
                        {detailLoadingId === item.id && (
                          <div className="absolute inset-0 flex items-center justify-center bg-white/70">
                            <div className="h-4 w-4 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
                          </div>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-semibold text-ink line-clamp-1">{item.title}</div>
                      <div className="text-[11px] text-muted">
                        {item.brand} {item.model} · {item.year}
                        {item.is_duplicate && (
                          <span className="ml-2 rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-bold text-amber-700">
                            Дубль
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-muted">{SOURCE_LABELS[item.source] ?? item.source}</td>
                    <td className="px-4 py-3 font-medium">{item.price.toLocaleString("uk-UA")} ₴</td>
                    <td className="px-4 py-3 text-muted">{item.region}</td>
                    <td className="px-4 py-3 text-muted whitespace-nowrap">{formatKyivDateTime(item.found_at)}</td>
                    <td className="px-4 py-3">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={e => e.stopPropagation()}
                        className="text-[12px] font-semibold text-emerald hover:underline"
                      >
                        Відкрити
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {totalPages > 1 && (
        <div className="mt-6 flex items-center justify-center gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage(p => p - 1)}
            className="rounded-lg border border-border px-3 py-1.5 text-[13px] disabled:opacity-40"
          >
            ←
          </button>
          <span className="text-[13px] text-muted">
            {page} / {totalPages}
          </span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => setPage(p => p + 1)}
            className="rounded-lg border border-border px-3 py-1.5 text-[13px] disabled:opacity-40"
          >
            →
          </button>
        </div>
      )}

      <ListingDetailModal
        listing={selectedListing}
        onClose={() => setSelectedListing(null)}
      />
    </div>
  );
}
