"use client";

import { useEffect, useId, useState } from "react";
import { ApiError, getApiErrorMessage, vin as vinApi } from "@/lib/api";
import { getVinCheck, saveVinCheck } from "@/lib/vin-check-cache";
import { UpgradeOffer } from "@/components/billing/UpgradeOffer";
import { cn } from "@/lib/utils";
import type { VinCheckResult } from "@/types/api";

const SEARCH_STEPS = [
  "Перевіряємо Базу ДАІ…",
  "Шукаємо аукціонну історію…",
  "Збираємо фото та звіти…",
] as const;

function VinSearchPreloader({ vin }: { vin: string }) {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => setElapsed(s => s + 1), 1000);
    return () => window.clearInterval(id);
  }, []);

  const stepIndex = elapsed < 4 ? 0 : elapsed < 12 ? 1 : 2;

  return (
    <div className="flex flex-col items-center py-10 text-center" role="status" aria-live="polite">
      <div
        className="h-11 w-11 animate-spin rounded-full border-[3px] border-emerald/20 border-t-emerald"
        aria-hidden
      />
      <p className="mt-4 text-[15px] font-semibold text-ink">Шукаємо авто за VIN…</p>
      <p className="mt-1 font-mono text-[12px] tracking-wide text-muted">{vin}</p>
      <p className="mt-4 text-[13px] font-medium text-emerald-dark">{SEARCH_STEPS[stepIndex]}</p>
      <ul className="mt-4 space-y-1.5 text-[12px] text-muted">
        {SEARCH_STEPS.map((label, idx) => (
          <li
            key={label}
            className={cn(
              "transition-colors",
              idx === stepIndex && "font-semibold text-ink",
              idx < stepIndex && "text-emerald-dark",
            )}
          >
            {idx < stepIndex ? "✓ " : idx === stepIndex ? "● " : "○ "}
            {label.replace("…", "")}
          </li>
        ))}
      </ul>
      <p className="mt-5 text-[12px] text-muted">
        {elapsed < 8
          ? "Зазвичай кілька секунд"
          : elapsed < 20
            ? "Аукціонна історія ще завантажується…"
            : "Ще шукаємо — не закривайте вікно"}
      </p>
    </div>
  );
}

type Props = {
  vin: string | null;
  listingId?: string | null;
  fallbackUrl?: string | null;
  open: boolean;
  onClose: () => void;
  onChecked?: (result: VinCheckResult) => void;
  onLoadingChange?: (loading: boolean) => void;
};

function Fact({ label, value }: { label: string; value?: string | number | null }) {
  if (value === null || value === undefined || value === "") return null;
  return (
    <div>
      <dt className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</dt>
      <dd className="mt-0.5 text-[14px] font-semibold text-ink">{value}</dd>
    </div>
  );
}

function AuctionPhotoGrid({
  photos,
  alt,
}: {
  photos: { url: string; caption?: string | null }[];
  alt?: string;
}) {
  if (photos.length === 0) return null;
  return (
    <div>
      <p className="mb-2 text-[12px] font-semibold text-ink">
        Фото аукціону · {photos.length}
      </p>
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
        {photos.map((photo, idx) => (
          <a
            key={`${photo.url}-${idx}`}
            href={photo.url}
            target="_blank"
            rel="noopener noreferrer"
            className="group block overflow-hidden rounded-lg"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={photo.url}
              alt={photo.caption || alt || `Фото ${idx + 1}`}
              className="aspect-[4/3] w-full object-cover transition group-hover:opacity-90"
            />
            {photo.caption ? (
              <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-muted">
                {photo.caption}
              </p>
            ) : null}
          </a>
        ))}
      </div>
    </div>
  );
}

function displacementLabel(value?: number | null): string | null {
  if (value == null) return null;
  return `${value} см³`;
}

function isVinLimitError(err: unknown): err is ApiError {
  return (
    err instanceof ApiError &&
    (err.status === 402 || err.code === "vin_check_limit" || /перевірк.*VIN|VIN.*ліміт/i.test(err.message))
  );
}

export function VinCheckPanel({
  vin,
  listingId,
  fallbackUrl,
  open,
  onClose,
  onChecked,
  onLoadingChange,
}: Props) {
  const titleId = useId();
  const [loading, setLoading] = useState(
    () => open && Boolean(vin) && !getVinCheck(vin),
  );
  const [error, setError] = useState<string | null>(null);
  const [limitReached, setLimitReached] = useState(false);
  const [data, setData] = useState<VinCheckResult | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (!open || !vin) {
      setLoading(false);
      setError(null);
      setLimitReached(false);
      setData(null);
      return;
    }

    let cancelled = false;
    const cached = getVinCheck(vin);
    if (cached) {
      setData(cached.result);
      setLoading(false);
      setError(null);
      setLimitReached(false);
      // Повторний перегляд уже перевіреного VIN — без нового запиту / квоти.
      return;
    }

    setLoading(true);
    setError(null);
    setLimitReached(false);
    setData(null);

    vinApi
      .lookup(vin)
      .then(result => {
        if (cancelled) return;
        saveVinCheck(vin, result, listingId);
        setData(result);
        onChecked?.(result);
      })
      .catch(err => {
        if (cancelled) return;
        if (isVinLimitError(err)) {
          setLimitReached(true);
          setError(err.message);
          return;
        }
        setError(getApiErrorMessage(err, "Не вдалося перевірити VIN"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, vin, listingId, onChecked]);

  useEffect(() => {
    onLoadingChange?.(open && Boolean(vin) && loading);
  }, [open, vin, loading, onLoadingChange]);

  if (!open) return null;

  const regionLabel = data?.region?.name_ua || data?.region?.name || null;
  const regionCodes = data?.region?.codes?.length ? data.region.codes.join(", ") : null;
  const title =
    data?.vendor || data?.model
      ? [data.vendor, data.model].filter(Boolean).join(" ")
      : "Перевірка VIN";
  const uniquePlates = data
    ? Array.from(
        new Set(
          data.operations.map(op => op.digits).filter((v): v is string => Boolean(v)),
        ),
      )
    : [];

  return (
    <div
      className="fixed inset-0 z-[140] flex items-end justify-center bg-ink/40 p-0 sm:items-center sm:p-4"
      role="presentation"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-busy={Boolean(vin && loading)}
        className="flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl border border-border bg-white shadow-xl sm:max-w-2xl sm:rounded-2xl"
        onClick={e => e.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-3 border-b border-border/70 px-5 py-4">
          <div className="min-w-0">
            <h2 id={titleId} className="truncate text-[16px] font-bold text-ink">
              {vin && loading ? "Перевірка VIN…" : title}
            </h2>
            {vin ? (
              <p className="mt-1 font-mono text-[12px] text-muted">{vin}</p>
            ) : (
              <p className="mt-1 text-[12px] text-muted">VIN у цьому оголошенні не вказано</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-lg px-2 py-1 text-[13px] font-semibold text-muted hover:bg-surface hover:text-ink"
            aria-label="Закрити"
          >
            Закрити
          </button>
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto px-5 py-4">
          {!vin && (
            <div className="space-y-4">
              <p className="text-[13px] leading-relaxed text-muted">
                Без повного VIN перевірка в Базі ДАІ недоступна. У багатьох оголошень AUTO.RIA VIN
                приховано — можна відкрити їхній звіт або знайти VIN у тексті оголошення.
              </p>
              {fallbackUrl && (
                <a
                  href={fallbackUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                >
                  Відкрити перевірку на AUTO.RIA
                </a>
              )}
            </div>
          )}

          {vin && loading && <VinSearchPreloader vin={vin} />}

          {vin && !loading && error && (
            <div className="space-y-4">
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] leading-relaxed text-amber-950">
                {error}
              </div>
              {limitReached && (
                <UpgradeOffer
                  planId="lite"
                  title="Необмежені перевірки VIN — тариф «Старт»"
                />
              )}
              {!limitReached && fallbackUrl && (
                <a
                  href={fallbackUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                >
                  Спробувати на AUTO.RIA
                </a>
              )}
            </div>
          )}

          {vin && !loading && data && (
            <div className="space-y-5">
              {data.is_stolen ? (
                <div className="rounded-xl border border-red-300 bg-red-50 px-4 py-3 text-[13px] font-semibold text-red-800">
                  У розшуку: авто позначено як викрадене в Базі ДАІ
                  {data.stolen_details?.length > 0 && (
                    <ul className="mt-2 space-y-1 font-normal">
                      {data.stolen_details.map((item, idx) => (
                        <li key={idx}>
                          {[item.theft_at, item.department_title, item.vendor_title, item.car_type]
                            .filter(Boolean)
                            .join(" · ")}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              ) : (
                <div className="rounded-xl border border-emerald/30 bg-emerald/10 px-4 py-3 text-[13px] font-semibold text-emerald-dark">
                  Не в розшуку — у Базі ДАІ немає відмітки про викрадення
                </div>
              )}

              {data.photo_url &&
                !(data.auction?.photos || []).some(photo => photo.url === data.photo_url) && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={data.photo_url}
                  alt={title}
                  className="h-36 w-full rounded-xl object-cover object-center"
                />
              )}

              <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                <Fact label="Номер" value={data.plate} />
                <Fact label="Марка" value={data.vendor} />
                <Fact label="Модель" value={data.model} />
                <Fact label="Рік" value={data.model_year} />
                <Fact label="Колір" value={data.color} />
                <Fact label="Об’єм" value={displacementLabel(data.displacement)} />
                <Fact label="Тип" value={data.kind_ua} />
                <Fact label="Регіон" value={regionLabel} />
                <Fact label="Коди регіону" value={regionCodes} />
                <Fact
                  label="Реєстрацій"
                  value={data.registrations_count > 0 ? data.registrations_count : null}
                />
                <Fact label="Перша реєстрація" value={data.first_registered_at} />
                <Fact label="Остання операція" value={data.last_registered_at} />
              </dl>

              {uniquePlates.length > 1 && (
                <div>
                  <h3 className="text-[13px] font-bold text-ink">Номери в історії</h3>
                  <p className="mt-1 font-mono text-[13px] leading-relaxed text-ink">
                    {uniquePlates.join(" · ")}
                  </p>
                </div>
              )}

              {data.operations.length > 0 && (
                <div>
                  <h3 className="text-[13px] font-bold text-ink">Історія реєстрацій</h3>
                  <ul className="mt-2 space-y-2">
                    {data.operations.map((op, idx) => (
                      <li
                        key={`${op.registered_at}-${idx}`}
                        className={cn(
                          "rounded-xl border border-border/80 px-3 py-2.5",
                          op.is_last && "border-emerald/40 bg-emerald/5",
                        )}
                      >
                        <div className="flex flex-wrap items-baseline justify-between gap-x-2 gap-y-0.5">
                          <span className="text-[13px] font-semibold text-ink">
                            {op.registered_at || "—"}
                          </span>
                          {op.digits && (
                            <span className="font-mono text-[12px] text-muted">{op.digits}</span>
                          )}
                        </div>
                        {op.operation_group_ua && (
                          <p className="mt-1 text-[11px] font-medium uppercase tracking-wide text-muted">
                            {op.operation_group_ua}
                          </p>
                        )}
                        <p className="mt-1 text-[13px] leading-snug text-ink">
                          {op.operation_ua || op.operation_ru || "Операція"}
                        </p>
                        <p className="mt-1 text-[12px] text-muted">
                          {[
                            op.color,
                            displacementLabel(op.displacement),
                            op.kind_ua,
                            op.department,
                            op.is_registered_to_company === true
                              ? "на компанію"
                              : op.is_registered_to_company === false
                                ? "на фізособу"
                                : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </p>
                        {op.address && (
                          <p className="mt-0.5 text-[12px] text-muted">{op.address}</p>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {data.note && (
                <p className="text-[12px] leading-relaxed text-muted">{data.note}</p>
              )}

              {data.auction && (
                <div className="space-y-3 rounded-xl border border-border/80 bg-surface/40 px-4 py-3">
                  <h3 className="text-[13px] font-bold text-ink">Аукціонна історія</h3>
                  {data.auction.title && (
                    <p className="text-[14px] font-semibold text-ink">
                      {data.auction.title.split("\n")[0]}
                      {data.auction.vin ? (
                        <span className="mt-0.5 block text-[12px] font-medium text-muted">
                          {data.auction.vin}
                        </span>
                      ) : null}
                    </p>
                  )}
                  {data.auction.meta_description && (
                    <p className="text-[12px] leading-relaxed text-muted">
                      {data.auction.meta_description}
                    </p>
                  )}
                  <AuctionPhotoGrid
                    photos={data.auction.photos || []}
                    alt={data.auction.title || title}
                  />
                  {!data.auction.photos?.length &&
                    data.auction.photo_url &&
                    data.auction.photo_url !== data.photo_url && (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={data.auction.photo_url}
                      alt={data.auction.title || "Аукціонне фото"}
                      className="h-36 w-full rounded-xl object-cover object-center"
                    />
                  )}
                  <dl className="grid grid-cols-2 gap-3">
                    <Fact label="Дата продажу" value={data.auction.sale_date} />
                    <Fact
                      label="Ціна продажу"
                      value={data.auction.sale_price ? `$ ${data.auction.sale_price}` : null}
                    />
                    <Fact
                      label="Пробіг"
                      value={
                        [data.auction.mileage, data.auction.mileage_km]
                          .filter(Boolean)
                          .join(" · ") || null
                      }
                    />
                    <Fact label="Записів про продаж" value={data.auction.sale_records} />
                    <Fact label="Двигун" value={data.auction.engine} />
                    <Fact label="Колір" value={data.auction.color} />
                    <Fact label="КПП" value={data.auction.transmission} />
                    <Fact label="Паливо" value={data.auction.fuel} />
                    <Fact label="Привід" value={data.auction.drive} />
                    <Fact label="Ключі" value={data.auction.keys} />
                    <Fact
                      label="Ремонт"
                      value={data.auction.repair_cost ? `$ ${data.auction.repair_cost}` : null}
                    />
                    <Fact
                      label="Ринкова"
                      value={data.auction.market_value ? `$ ${data.auction.market_value}` : null}
                    />
                    <Fact
                      label="Пошкодження"
                      value={
                        [
                          data.auction.primary_damage,
                          data.auction.primary_damage_en &&
                          data.auction.primary_damage_en !== data.auction.primary_damage
                            ? data.auction.primary_damage_en
                            : null,
                        ]
                          .filter(Boolean)
                          .join(" · ") || null
                      }
                    />
                    <Fact label="Стан" value={data.auction.exterior_condition} />
                    <Fact
                      label="Сер. ціна"
                      value={data.auction.avg_price ? `$ ${data.auction.avg_price}` : null}
                    />
                    <Fact label="Лот" value={data.auction.lot_id} />
                  </dl>
                  <div className="flex flex-wrap gap-x-4 gap-y-2">
                    {data.auction.page_url && (
                      <a
                        href={data.auction.page_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                      >
                        Звіт AutoHelperBot
                      </a>
                    )}
                    {(data.auction.links?.copart || data.auction.copart_url) && (
                      <a
                        href={data.auction.links?.copart || data.auction.copart_url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                      >
                        Copart
                      </a>
                    )}
                    {(data.auction.links?.iaai || data.auction.iaai_url) && (
                      <a
                        href={data.auction.links?.iaai || data.auction.iaai_url || "#"}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                      >
                        IAAI
                      </a>
                    )}
                    {data.auction.links?.carhistory && (
                      <a
                        href={data.auction.links.carhistory}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                      >
                        CarHistory
                      </a>
                    )}
                    {data.auction.links?.autocheck && (
                      <a
                        href={data.auction.links.autocheck}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                      >
                        Autocheck
                      </a>
                    )}
                    {data.auction.links?.window_sticker && (
                      <a
                        href={data.auction.links.window_sticker}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
                      >
                        Window sticker
                      </a>
                    )}
                  </div>
                </div>
              )}

              <a
                href={data.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
              >
                {data.auction && !data.operations.length
                  ? "Відкрити джерело"
                  : "Відкрити на База ДАІ"}
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
