"use client";

import { useEffect, useId, useState } from "react";
import { getApiErrorMessage, vin as vinApi } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { VinCheckResult } from "@/types/api";

type Props = {
  vin: string | null;
  fallbackUrl?: string | null;
  open: boolean;
  onClose: () => void;
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

function displacementLabel(value?: number | null): string | null {
  if (value == null) return null;
  return `${value} см³`;
}

export function VinCheckPanel({ vin, fallbackUrl, open, onClose }: Props) {
  const titleId = useId();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
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
      setData(null);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    vinApi
      .lookup(vin)
      .then(result => {
        if (!cancelled) setData(result);
      })
      .catch(err => {
        if (!cancelled) setError(getApiErrorMessage(err, "Не вдалося перевірити VIN"));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [open, vin]);

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
        className="flex max-h-[92vh] w-full max-w-lg flex-col overflow-hidden rounded-t-2xl border border-border bg-white shadow-xl sm:rounded-2xl"
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

          {vin && loading && (
            <p className="py-8 text-center text-[14px] text-muted">Запит до Бази ДАІ…</p>
          )}

          {vin && !loading && error && (
            <div className="space-y-4">
              <div className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-[13px] leading-relaxed text-amber-950">
                {error}
              </div>
              {fallbackUrl && (
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

              {data.photo_url && (
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

              <a
                href={data.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex text-[13px] font-semibold text-emerald-dark underline-offset-2 hover:underline"
              >
                Відкрити на База ДАІ
              </a>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
