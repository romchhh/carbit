"use client";

import { cn } from "@/lib/utils";
import type { StoredVinCheck } from "@/lib/vin-check-cache";

type Props = {
  cached: StoredVinCheck;
  className?: string;
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void;
};

function formatCheckedAt(iso: string): string {
  try {
    return new Intl.DateTimeFormat("uk-UA", {
      day: "numeric",
      month: "short",
      hour: "2-digit",
      minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return "";
  }
}

export function VinCheckSummary({ cached, className, onClick }: Props) {
  const { result, checkedAt } = cached;
  const title = [result.vendor, result.model].filter(Boolean).join(" ");
  const auction = result.auction;
  const photos = (auction?.photos?.length ? auction.photos : []).filter(p => p.url);
  const hero = photos[0]?.url || auction?.photo_url || result.photo_url || null;
  const region = result.region?.name_ua || result.region?.name || null;
  const damage = auction?.primary_damage || auction?.primary_damage_en || null;
  const sale = auction?.sale_price ? `$ ${auction.sale_price}` : null;
  const facts = [
    result.model_year ? String(result.model_year) : null,
    result.color || auction?.color,
    sale ? `продаж ${sale}` : null,
    damage,
    result.registrations_count > 0 ? `${result.registrations_count} реєстр.` : null,
    region,
  ].filter(Boolean);

  const content = (
    <>
      {hero && photos.length === 0 && (
        <div className="mb-2">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={hero} alt="" className="h-16 w-full rounded-lg object-cover" />
        </div>
      )}
      {photos.length > 0 && (
        <div
          className={cn(
            "mb-2 grid gap-1",
            photos.length <= 1 ? "grid-cols-1" : photos.length === 2 ? "grid-cols-2" : "grid-cols-3",
          )}
        >
          {photos.slice(0, 6).map((photo, idx, arr) => (
            <div key={`${photo.url}-${idx}`} className="relative">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={photo.url} alt="" className="h-16 w-full rounded-lg object-cover" />
              {idx === arr.length - 1 && photos.length > 6 && (
                <span className="absolute inset-0 flex items-center justify-center rounded-lg bg-ink/55 text-[11px] font-bold text-white">
                  +{photos.length - 6}
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
            result.is_stolen ? "bg-red-600 text-white" : "bg-emerald text-white",
          )}
        >
          {result.is_stolen ? "У розшуку" : "ДАІ: ок"}
        </span>
        {auction && (
          <span className="rounded-full bg-ink px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white">
            Аукціон
          </span>
        )}
        {photos.length > 0 && (
          <span className="text-[10px] font-medium text-muted">{photos.length} фото</span>
        )}
        <span className="text-[10px] text-muted">{formatCheckedAt(checkedAt)}</span>
      </div>

      {(title || facts.length > 0) && (
        <p className="mt-1.5 text-[12px] font-semibold leading-snug text-ink">
          {title || auction?.title?.split("\n")[0] || "Перевірка VIN"}
          {facts.length > 0 && (
            <span className="font-normal text-muted"> · {facts.join(" · ")}</span>
          )}
        </p>
      )}

      {(result.plate || result.vin) && (
        <p className="mt-0.5 font-mono text-[11px] text-muted">
          {[result.plate, result.vin].filter(Boolean).join(" · ")}
        </p>
      )}
    </>
  );

  const boxClass = cn(
    "w-full rounded-xl border px-3 py-2.5 text-left transition-colors",
    result.is_stolen
      ? "border-red-200 bg-red-50 hover:border-red-300"
      : "border-emerald/25 bg-emerald/5 hover:border-emerald/40",
    className,
  );

  if (onClick) {
    return (
      <button type="button" onClick={onClick} className={cn(boxClass, "cursor-pointer")}>
        {content}
      </button>
    );
  }

  return <div className={boxClass}>{content}</div>;
}
