"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { AppPage, AppSection } from "@/components/layout/AppPage";
import { VinCheckPanel } from "@/components/listings/VinCheckPanel";
import { UpgradeOffer } from "@/components/billing/UpgradeOffer";
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
        <ul className="mt-3 divide-y divide-border/60">
          {items.map((item, idx) => (
            <li key={`${item.vin}-${item.checked_at || idx}`}>
              <button
                type="button"
                onClick={() => onSelect(item.vin)}
                className="flex w-full items-center gap-3 py-3 text-left transition-colors hover:bg-white/70"
              >
                {item.photo_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={item.photo_url}
                    alt=""
                    className="h-12 w-14 shrink-0 rounded-lg object-cover"
                  />
                ) : (
                  <div className="flex h-12 w-14 shrink-0 items-center justify-center rounded-lg bg-surface text-[11px] font-bold text-muted">
                    VIN
                  </div>
                )}
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px] font-semibold text-ink">
                    {item.title || "Авто за VIN"}
                  </div>
                  <div className="mt-0.5 font-mono text-[11px] text-muted">{item.vin}</div>
                  <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px] text-muted">
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
  const [limitReached, setLimitReached] = useState(false);
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
    setLimitReached(false);
    setActiveVin(code);
    setSearching(true);
    setPanelOpen(true);
  };

  const onSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (quota && !quota.unlimited && (quota.remaining ?? 0) <= 0) {
      setLimitReached(true);
      setFormError(
        `Безкоштовно доступно ${quota.limit ?? 3} перевірки VIN. Оформіть тариф «Старт» — без обмежень.`,
      );
      return;
    }
    openVin(input);
  };

  return (
    <AppPage
      wide
      title="Перевірка VIN"
      description="База ДАІ та аукціонна історія. Безкоштовно — 3 унікальні VIN; на підписці Старт і вище — безліміт."
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
          {quota && (
            <p className="text-[12px] text-muted">
              {quota.unlimited
                ? "На вашому тарифі перевірки VIN без обмежень."
                : `Використано ${quota.used} з ${quota.limit ?? 3} безкоштовних перевірок` +
                  (quota.remaining != null ? ` · залишилось ${quota.remaining}` : "")}
            </p>
          )}
          {formError && (
            <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] text-amber-950">
              {formError}
            </div>
          )}
          {limitReached && (
            <UpgradeOffer planId="lite" title="Необмежені перевірки VIN — тариф «Старт»" />
          )}
        </form>
      </AppSection>

      <div className="grid gap-4 lg:grid-cols-2">
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
