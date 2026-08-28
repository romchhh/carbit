"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppPage, AppSection } from "@/components/layout/AppPage";
import { VinCheckPanel } from "@/components/listings/VinCheckPanel";
import { vin as vinApi } from "@/lib/api";
import { normalizeVin } from "@/lib/vin-check";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";
import type { VinCheckHistoryItem, VinQuotaStatus } from "@/types/api";

function HistoryList({
  title,
  empty,
  items,
  onSelect,
}: {
  title: string;
  empty: string;
  items: VinCheckHistoryItem[];
  onSelect: (vin: string) => void;
}) {
  return (
    <AppSection>
      <h2 className="text-[15px] font-semibold text-ink">{title}</h2>
      {items.length === 0 ? (
        <p className="mt-3 text-[13px] text-muted">{empty}</p>
      ) : (
        <div className="-mx-1 mt-3 overflow-x-auto overscroll-x-contain pb-1 [-ms-overflow-style:none] [scrollbar-width:thin]">
          <ul className="flex w-max min-w-full gap-2.5 px-1">
            {items.map((item, idx) => (
              <li key={`${item.vin}-${item.checked_at || idx}`} className="w-[220px] shrink-0 sm:w-[240px]">
                <button
                  type="button"
                  onClick={() => onSelect(item.vin)}
                  className="flex h-full w-full items-start gap-3 rounded-xl border border-border/70 bg-white px-3 py-3 text-left transition-colors hover:border-emerald/35 hover:bg-emerald/5"
                >
                  {item.photo_url ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={item.photo_url}
                      alt=""
                      className="h-14 w-16 shrink-0 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="flex h-14 w-16 shrink-0 items-center justify-center rounded-lg bg-surface text-[11px] font-bold text-muted">
                      VIN
                    </div>
                  )}
                  <div className="min-w-0 flex-1">
                    <div className="line-clamp-2 text-[13px] font-semibold leading-snug text-ink">
                      {item.title || "Авто за VIN"}
                    </div>
                    <div className="mt-0.5 truncate font-mono text-[11px] text-muted">{item.vin}</div>
                    <div className="mt-1.5 flex flex-wrap items-center gap-1.5 text-[11px] text-muted">
                      {item.checked_at && <span>{formatKyivDateTime(item.checked_at)}</span>}
                      {item.is_stolen && (
                        <span className="rounded-md bg-red-50 px-1.5 py-0.5 font-semibold text-red-700">
                          Розшук
                        </span>
                      )}
                      {item.has_auction && (
                        <span className="rounded-md bg-emerald/10 px-1.5 py-0.5 font-semibold text-emerald-dark">
                          Аукціон
                        </span>
                      )}
                      {item.color && <span>{item.color}</span>}
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </AppSection>
  );
}

export default function VinCheckPage() {
  const [input, setInput] = useState("");
  const [activeVin, setActiveVin] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [searching, setSearching] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [quota, setQuota] = useState<VinQuotaStatus | null>(null);
  const [mine, setMine] = useState<VinCheckHistoryItem[]>([]);
  const [recent, setRecent] = useState<VinCheckHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(true);

  const refreshMeta = useCallback(async () => {
    setLoadingHistory(true);
    try {
      const [q, my, all] = await Promise.all([
        vinApi.quota().catch(() => null),
        vinApi.myHistory(20).catch(() => ({ items: [] as VinCheckHistoryItem[] })),
        vinApi.recentHistory(20).catch(() => ({ items: [] as VinCheckHistoryItem[] })),
      ]);
      setQuota(q);
      setMine(my.items);
      setRecent(all.items);
    } finally {
      setLoadingHistory(false);
    }
  }, []);

  useEffect(() => {
    void refreshMeta();
  }, [refreshMeta]);

  const openVin = (raw: string) => {
    const code = normalizeVin(raw);
    if (!code) {
      setFormError("Введіть коректний VIN (17 символів, без I/O/Q)");
      return;
    }
    setFormError(null);
    setActiveVin(code);
    setSearching(true);
    setPanelOpen(true);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    openVin(input);
  };

  return (
    <AppPage
      wide
      title="Перевірка VIN"
      description="База ДАІ та аукціонна історія. Перевірки VIN без обмежень на всіх тарифах."
    >
      <AppSection className="mb-4">
        <form onSubmit={onSubmit} className="space-y-3">
          <label className="block text-[12px] font-semibold uppercase tracking-wide text-muted">
            VIN-код
          </label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              value={input}
              disabled={searching}
              onChange={e => {
                setInput(e.target.value.toUpperCase().replace(/[^A-HJ-NPR-Z0-9]/gi, "").slice(0, 17));
                setFormError(null);
              }}
              placeholder="Наприклад WAUDACF53RA037339"
              autoComplete="off"
              spellCheck={false}
              className={cn(
                "w-full rounded-xl border border-border bg-white px-4 py-3 font-mono text-[15px] tracking-wide text-ink outline-none",
                "placeholder:font-sans placeholder:tracking-normal placeholder:text-muted",
                "focus:border-emerald focus:ring-2 focus:ring-emerald/20",
                "disabled:bg-surface disabled:text-muted",
              )}
            />
            <button
              type="submit"
              disabled={searching}
              className="inline-flex shrink-0 items-center justify-center gap-2 rounded-full bg-emerald px-5 py-3 text-[14px] font-bold text-white transition-colors hover:bg-emerald-dark disabled:cursor-wait disabled:opacity-80 sm:min-w-[140px]"
            >
              {searching ? (
                <>
                  <span
                    className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white"
                    aria-hidden
                  />
                  Пошук…
                </>
              ) : (
                "Перевірити"
              )}
            </button>
          </div>
          {quota && quota.used > 0 && (
            <p className="text-[12px] text-muted">
              Перевірок у вашому акаунті: {quota.used}. Лімітів немає — на всіх тарифах.
            </p>
          )}
          {formError && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-950">
              {formError}
            </div>
          )}
        </form>
      </AppSection>

      <div className="flex flex-col gap-4">
        <HistoryList
          title="Ваші останні перевірки"
          empty={loadingHistory ? "Завантаження…" : "Ще немає перевірок — введіть VIN вище."}
          items={mine}
          onSelect={openVin}
        />
        <HistoryList
          title="Останні перевірки в системі"
          empty={loadingHistory ? "Завантаження…" : "Поки ніхто не перевіряв VIN."}
          items={recent}
          onSelect={openVin}
        />
      </div>

      <VinCheckPanel
        vin={activeVin}
        open={panelOpen}
        onLoadingChange={setSearching}
        onClose={() => {
          setPanelOpen(false);
          setSearching(false);
          void refreshMeta();
        }}
        onChecked={() => {
          setSearching(false);
          void refreshMeta();
        }}
      />
    </AppPage>
  );
}
