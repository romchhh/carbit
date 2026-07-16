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
  const region = result.region?.name_ua || result.region?.name || null;
  const facts = [
    result.model_year ? String(result.model_year) : null,
    result.color,
    result.registrations_count > 0 ? `${result.registrations_count} реєстр.` : null,
    region,
  ].filter(Boolean);

  const content = (
    <>
      <div className="flex flex-wrap items-center gap-2">
        <span
          className={cn(
            "rounded-full px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide",
            result.is_stolen ? "bg-red-600 text-white" : "bg-emerald text-white",
          )}
        >
          {result.is_stolen ? "У розшуку" : "ДАІ: ок"}
        </span>
        <span className="text-[10px] text-muted">
          {formatCheckedAt(checkedAt)}
        </span>
      </div>

      {(title || facts.length > 0) && (
        <p className="mt-1.5 text-[12px] font-semibold leading-snug text-ink">
          {title || "Перевірка VIN"}
          {facts.length > 0 && (
            <span className="font-normal text-muted"> · {facts.join(" · ")}</span>
          )}
        </p>
      )}

      {result.plate && (
        <p className="mt-0.5 font-mono text-[11px] text-muted">
          {result.plate}
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
