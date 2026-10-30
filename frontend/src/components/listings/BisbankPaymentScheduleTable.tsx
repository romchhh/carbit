"use client";

import {
  formatBisbankDateUk,
  formatMoneyTableUah,
  type BisbankPaymentScheduleRow,
} from "@/lib/bisbank-credit-calculator";

type Props = {
  schedule: BisbankPaymentScheduleRow[];
  className?: string;
};

export function BisbankPaymentScheduleTable({ schedule, className }: Props) {
  const payments = schedule.filter(r => r.index > 0);
  if (payments.length === 0) return null;

  return (
    <div className={className}>
      <div className="overflow-x-auto rounded-xl border border-border/80">
        <table className="w-full min-w-[640px] border-collapse text-left text-[11px]">
          <thead>
            <tr className="border-b border-border/80 bg-surface/80 text-[10px] font-semibold uppercase tracking-wide text-muted">
              <th className="px-2 py-2">№</th>
              <th className="px-2 py-2">Дата платежу</th>
              <th className="px-2 py-2 text-right">Днів</th>
              <th className="px-2 py-2 text-right">Залишок</th>
              <th className="px-2 py-2 text-right">Тіло</th>
              <th className="px-2 py-2 text-right">Відсотки</th>
              <th className="px-2 py-2 text-right">Платіж</th>
            </tr>
          </thead>
          <tbody className="tabular-nums text-ink">
            {schedule
              .filter(r => r.index === 0)
              .map(row => (
                <tr key="disb" className="border-b border-border/50 bg-emerald-light/20">
                  <td className="px-2 py-1.5 text-muted">0</td>
                  <td className="px-2 py-1.5">{formatBisbankDateUk(row.paymentDate)}</td>
                  <td className="px-2 py-1.5 text-right text-muted">—</td>
                  <td className="px-2 py-1.5 text-right">
                    {formatMoneyTableUah(row.balanceBeforeUah)}
                  </td>
                  <td className="px-2 py-1.5 text-right text-muted">—</td>
                  <td className="px-2 py-1.5 text-right text-muted">—</td>
                  <td className="px-2 py-1.5 text-right font-medium text-emerald-dark">
                    +{formatMoneyTableUah(row.cashflowUah)}
                    {row.oneTimeFeeUah > 0 ? (
                      <span className="block text-[9px] font-normal text-muted">
                        ком. {formatMoneyTableUah(row.oneTimeFeeUah)}
                      </span>
                    ) : null}
                  </td>
                </tr>
              ))}
            {payments.map(row => (
              <tr key={row.index} className="border-b border-border/40 last:border-0">
                <td className="px-2 py-1.5">{row.index}</td>
                <td className="px-2 py-1.5 whitespace-nowrap">
                  {formatBisbankDateUk(row.paymentDate)}
                </td>
                <td className="px-2 py-1.5 text-right text-muted">{row.daysInPeriod ?? "—"}</td>
                <td className="px-2 py-1.5 text-right">
                  {formatMoneyTableUah(row.balanceBeforeUah)}
                </td>
                <td className="px-2 py-1.5 text-right">{formatMoneyTableUah(row.principalUah)}</td>
                <td className="px-2 py-1.5 text-right">{formatMoneyTableUah(row.interestUah)}</td>
                <td className="px-2 py-1.5 text-right font-semibold">
                  {formatMoneyTableUah(row.paymentTotalUah)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-2 text-[10px] leading-snug text-muted">
        Структура колонок як у листі «Графік платежів» калькулятора БІЗБАНК. Дата платежу — 10-те
        число відповідного місяця; перший період — від дати кредиту.
      </p>
    </div>
  );
}
