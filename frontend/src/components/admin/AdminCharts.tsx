"use client";

import { cn } from "@/lib/utils";

type Point = { date: string; count: number };

export function AdminBarChart({
  data,
  colorClass = "bg-emerald",
  height = 128,
  compact,
}: {
  data: Point[];
  colorClass?: string;
  height?: number;
  /** Вужчі стовпці + горизонтальний скрол для довгих періодів (30+ днів) */
  compact?: boolean;
}) {
  const max = Math.max(...data.map(d => d.count), 1);
  const isCompact = compact ?? data.length > 14;
  const barWidth = isCompact ? 22 : undefined;

  const chart = (
    <div
      className={cn("flex items-end", isCompact ? "gap-1" : "gap-2")}
      style={{
        height,
        minWidth: isCompact ? data.length * 26 : undefined,
      }}
    >
      {data.map(({ date, count }, index) => (
        <div
          key={`${date}-${index}`}
          className={cn("flex flex-col items-center gap-1", !isCompact && "flex-1")}
          style={barWidth ? { width: barWidth, flexShrink: 0 } : undefined}
        >
          <span className="text-[10px] font-semibold text-ink/70">{count || ""}</span>
          <div
            className={cn("w-full rounded-t-md transition-all min-h-[4px]", colorClass)}
            style={{ height: `${(count / max) * 100}%` }}
            title={`${date}: ${count}`}
          />
          <span className="text-[10px] text-muted whitespace-nowrap">
            {!isCompact || index % 5 === 0 || index === data.length - 1 ? date : ""}
          </span>
        </div>
      ))}
    </div>
  );

  if (isCompact) {
    return <div className="overflow-x-auto pb-1">{chart}</div>;
  }
  return chart;
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
