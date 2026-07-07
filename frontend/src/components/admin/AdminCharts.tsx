"use client";

import { cn } from "@/lib/utils";

type Point = { date: string; count: number };

export function AdminBarChart({
  data,
  colorClass = "bg-emerald",
  height = 128,
}: {
  data: Point[];
  colorClass?: string;
  height?: number;
}) {
  const max = Math.max(...data.map(d => d.count), 1);

  return (
    <div className="flex items-end gap-2" style={{ height }}>
      {data.map(({ date, count }) => (
        <div key={date} className="flex flex-1 flex-col items-center gap-1">
          <span className="text-[10px] font-semibold text-ink/70">{count || ""}</span>
          <div
            className={cn("w-full rounded-t-md transition-all min-h-[4px]", colorClass)}
            style={{ height: `${(count / max) * 100}%` }}
            title={`${date}: ${count}`}
          />
          <span className="text-[10px] text-muted">{date}</span>
        </div>
      ))}
    </div>
  );
}

export function AdminStatusBadge({ status }: { status: string }) {
  const styles: Record<string, string> = {
    ok: "bg-emerald/15 text-emerald-dark",
    running: "bg-blue-100 text-blue-700",
    delayed: "bg-amber-100 text-amber-700",
    stale: "bg-red-100 text-red-600",
    unknown: "bg-surface text-muted",
  };
  const labels: Record<string, string> = {
    ok: "В нормі",
    running: "Парсинг…",
    delayed: "Затримка",
    stale: "Давно не було",
    unknown: "Невідомо",
  };

  return (
    <span className={cn("rounded-full px-2.5 py-1 text-[11px] font-bold uppercase", styles[status] ?? styles.unknown)}>
      {labels[status] ?? status}
    </span>
  );
}
