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

type AreaPoint = { label: string; total: number; unique?: number };

export function AdminAreaChart({
  data,
  height = 180,
  strokeClass = "stroke-emerald",
  fillClass = "fill-emerald/15",
  showUnique = false,
}: {
  data: AreaPoint[];
  height?: number;
  strokeClass?: string;
  fillClass?: string;
  showUnique?: boolean;
}) {
  if (!data.length) {
    return <div className="text-[13px] text-muted">Немає даних за період</div>;
  }

  const width = 640;
  const padX = 8;
  const padY = 18;
  const innerW = width - padX * 2;
  const innerH = height - padY * 2;
  const max = Math.max(...data.map(d => d.total), 1);

  const coords = data.map((point, index) => {
    const x = padX + (index / Math.max(data.length - 1, 1)) * innerW;
    const y = padY + innerH - (point.total / max) * innerH;
    return { x, y, point };
  });

  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x.toFixed(1)} ${c.y.toFixed(1)}`).join(" ");
  const area = `${line} L ${coords[coords.length - 1]?.x.toFixed(1)} ${(padY + innerH).toFixed(1)} L ${coords[0]?.x.toFixed(1)} ${(padY + innerH).toFixed(1)} Z`;

  const labelEvery = data.length > 16 ? Math.ceil(data.length / 8) : data.length > 8 ? 2 : 1;

  return (
    <div className="space-y-2">
      <svg viewBox={`0 0 ${width} ${height}`} className="w-full" role="img" aria-label="Графік відвідувань">
        <defs>
          <linearGradient id="areaGradient" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#00C896" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#00C896" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0.25, 0.5, 0.75, 1].map(ratio => (
          <line
            key={ratio}
            x1={padX}
            x2={width - padX}
            y1={padY + innerH * (1 - ratio)}
            y2={padY + innerH * (1 - ratio)}
            className="stroke-border/70"
            strokeWidth="1"
            strokeDasharray="4 4"
          />
        ))}
        <path d={area} fill="url(#areaGradient)" />
        <path d={line} fill="none" className={cn(strokeClass, "stroke-[2.5]")} strokeLinecap="round" strokeLinejoin="round" />
        {coords.map(({ x, y, point }, index) => (
          <g key={`${point.label}-${index}`}>
            <circle cx={x} cy={y} r="3.5" className="fill-white stroke-emerald stroke-[2]" />
            <title>
              {point.label}: {point.total}
              {showUnique && point.unique != null ? ` (унік.: ${point.unique})` : ""}
            </title>
          </g>
        ))}
      </svg>
      <div className="flex justify-between text-[10px] text-muted px-1">
        {data.map((point, index) =>
          index % labelEvery === 0 || index === data.length - 1 ? (
            <span key={`${point.label}-${index}`}>{point.label}</span>
          ) : null,
        )}
      </div>
    </div>
  );
}

export function AdminHorizontalBars({
  rows,
  colorClass = "bg-emerald",
  valueLabel,
}: {
  rows: { label: string; sublabel?: string; count: number; share?: number }[];
  colorClass?: string;
  valueLabel?: (count: number, share?: number) => string;
}) {
  const max = Math.max(...rows.map(row => row.count), 1);

  if (!rows.length) {
    return <div className="text-[13px] text-muted">Немає даних</div>;
  }

  return (
    <div className="space-y-3">
      {rows.map(row => (
        <div key={row.label + (row.sublabel ?? "")}>
          <div className="mb-1 flex items-center justify-between gap-3 text-[12px]">
            <div className="min-w-0">
              <div className="truncate font-medium text-ink">{row.label}</div>
              {row.sublabel ? <div className="truncate text-[11px] text-muted">{row.sublabel}</div> : null}
            </div>
            <div className="shrink-0 font-semibold tabular-nums text-ink">
              {valueLabel ? valueLabel(row.count, row.share) : row.count}
            </div>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-surface">
            <div
              className={cn("h-full rounded-full transition-all", colorClass)}
              style={{ width: `${Math.max((row.count / max) * 100, row.count ? 4 : 0)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

export function AdminHeatmapHours({
  rows,
}: {
  rows: { hour: number; label: string; count: number }[];
}) {
  const max = Math.max(...rows.map(row => row.count), 1);

  return (
    <div className="grid grid-cols-6 gap-2 sm:grid-cols-8 lg:grid-cols-12">
      {rows.map(row => {
        const intensity = row.count / max;
        return (
          <div
            key={row.hour}
            title={`${row.label}: ${row.count}`}
            className="rounded-xl border border-border/60 p-2 text-center"
            style={{
              backgroundColor: `rgba(0, 200, 150, ${0.08 + intensity * 0.55})`,
            }}
          >
            <div className="text-[10px] font-medium text-muted">{row.label}</div>
            <div className="mt-1 text-[14px] font-black text-ink">{row.count || "·"}</div>
          </div>
        );
      })}
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
