"use client";

import { getBazaGaiVinUrl } from "@/lib/vin-check";
import type { VinCheckResult } from "@/types/api";

type Props = {
  result: VinCheckResult;
  className?: string;
};

export function VinCheckResultView({ result, className }: Props) {
  return (
    <div className={className}>
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
        <p className="text-[15px] font-bold text-ink sm:text-[16px]">
          {[result.vendor, result.model].filter(Boolean).join(" ") || "Авто з Бази ДАІ"}
          {result.model_year ? ` · ${result.model_year}` : ""}
        </p>
        {result.is_stolen && (
          <span className="rounded-full bg-red-50 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide text-red-700">
            В угні
          </span>
        )}
      </div>
      <p className="mt-1 font-mono text-[12px] text-muted">VIN: {result.vin}</p>
      {result.digits && (
        <p className="mt-1 text-[13px] text-ink/85">
          Номер: <span className="font-semibold">{result.digits}</span>
        </p>
      )}
      {result.region && <p className="mt-0.5 text-[13px] text-ink/85">Регіон: {result.region}</p>}
      <p className="mt-0.5 text-[13px] text-ink/85">
        Розшук:{" "}
        <span
          className={
            result.is_stolen ? "font-semibold text-red-700" : "font-semibold text-emerald-dark"
          }
        >
          {result.is_stolen ? "так" : "ні"}
        </span>
      </p>

      {result.stolen_details.length > 0 && (
        <ul className="mt-3 space-y-1 rounded-xl bg-red-50/80 p-3 text-[12px] text-red-800">
          {result.stolen_details.slice(0, 3).map((item, idx) => (
            <li key={`${item.theft_at}-${idx}`}>
              {[item.theft_at, item.vendor_title, item.department_title].filter(Boolean).join(" · ")}
            </li>
          ))}
        </ul>
      )}

      {result.operations.length > 0 && (
        <div className="mt-4">
          <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-muted">
            Реєстрації
          </p>
          <ul className="space-y-2">
            {result.operations.slice(0, 5).map((op, idx) => (
              <li
                key={`${op.registered_at}-${idx}`}
                className="rounded-xl bg-surface/80 px-3 py-2 text-[12px] leading-snug text-ink/85"
              >
                <span className="font-semibold text-ink">
                  {[op.registered_at, op.operation_group || op.operation].filter(Boolean).join(" · ")}
                </span>
                {(op.color || op.address || op.department) && (
                  <span className="mt-0.5 block text-muted">
                    {[op.color, op.department, op.address].filter(Boolean).join(" · ")}
                  </span>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!result.operations.length && !result.is_stolen && (
        <p className="mt-3 text-[13px] text-muted">Дані знайдено, детальних операцій немає.</p>
      )}

      <a
        href={result.source_url || getBazaGaiVinUrl(result.vin)}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-4 inline-flex text-[13px] font-semibold text-emerald-dark hover:underline"
      >
        Відкрити на Базі ДАІ →
      </a>
    </div>
  );
}
