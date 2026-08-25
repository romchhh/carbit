"use client";

import { useMemo, useState } from "react";
import { IosToggle } from "@/components/ui/IosToggle";
import { cn } from "@/lib/utils";
import type { PublishedWithinDaysValue } from "@/lib/search-catalog";
import {
  PUBLISHED_MONTHS,
  PUBLISHED_PRESET_OPTIONS,
  PUBLISHED_WEEKDAYS,
  applyCalendarDay,
  formatLocalDateTime,
  formatPublishedDateTimeLabel,
  formatPublishedFilterSummary,
  getCalendarDays,
  hasCustomPublishedRange,
  isDayInPublishedRange,
  normalizePublishedRange,
  parseLocalDateTime,
  sameCalendarDay,
} from "@/lib/published-date-filter";

type Props = {
  publishedWithinDays: PublishedWithinDaysValue;
  publishedFrom: string;
  publishedTo: string;
  onChange: (patch: {
    publishedWithinDays?: PublishedWithinDaysValue;
    publishedFrom?: string;
    publishedTo?: string;
  }) => void;
};

type ActiveField = "from" | "to";

export function FilterPublishedDateRange({
  publishedWithinDays,
  publishedFrom,
  publishedTo,
  onChange,
}: Props) {
  const customActive = hasCustomPublishedRange(publishedFrom, publishedTo);
  const [activeField, setActiveField] = useState<ActiveField>("from");
  const anchorDate = parseLocalDateTime(
    activeField === "from" ? publishedFrom || publishedTo : publishedTo || publishedFrom,
  );
  const [viewMonth, setViewMonth] = useState(() => {
    const base = anchorDate ?? new Date();
    return { year: base.getFullYear(), month: base.getMonth() };
  });

  const summary = formatPublishedFilterSummary(publishedWithinDays, publishedFrom, publishedTo);
  const calendarDays = useMemo(
    () => getCalendarDays(viewMonth.year, viewMonth.month),
    [viewMonth.month, viewMonth.year],
  );

  const shiftMonth = (delta: number) => {
    setViewMonth(current => {
      const next = new Date(current.year, current.month + delta, 1);
      return { year: next.getFullYear(), month: next.getMonth() };
    });
  };

  const selectPreset = (value: PublishedWithinDaysValue) => {
    onChange({
      publishedWithinDays: value,
      publishedFrom: "",
      publishedTo: "",
    });
  };

  const updateCustom = (from: string, to: string) => {
    const normalized = normalizePublishedRange(from, to);
    onChange({
      publishedWithinDays: "",
      publishedFrom: normalized.from,
      publishedTo: normalized.to,
    });
  };

  const handleDayClick = (day: Date) => {
    const next = applyCalendarDay(day, activeField, publishedFrom, publishedTo);
    updateCustom(next.from, next.to);
  };

  const clearAll = () => {
    onChange({ publishedWithinDays: "", publishedFrom: "", publishedTo: "" });
  };

  const setQuickRange = (daysBack: number) => {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - daysBack);
    start.setHours(0, 0, 0, 0);
    end.setHours(23, 59, 0, 0);
    updateCustom(formatLocalDateTime(start), formatLocalDateTime(end));
  };

  const setWithinDaysToggle = (days: "15" | "30", enabled: boolean) => {
    if (customActive) return;
    if (enabled) {
      selectPreset(days);
      return;
    }
    if (publishedWithinDays === days) {
      selectPreset("");
    }
  };

  return (
    <div className="space-y-3 rounded-xl border border-border/60 bg-surface/20 p-3">
      <div className="space-y-2 rounded-xl border border-border/70 bg-white p-3">
        <p className="text-[12px] font-semibold text-ink">Вік оголошення</p>
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <span className="text-[13px] font-medium text-ink">Показувати до 15 днів</span>
          <IosToggle
            checked={!customActive && publishedWithinDays === "15"}
            disabled={customActive}
            aria-label="Показувати оголошення до 15 днів"
            onChange={checked => setWithinDaysToggle("15", checked)}
          />
        </div>
        <div className="flex items-center justify-between gap-3 rounded-lg px-0.5 py-1">
          <span className="text-[13px] font-medium text-ink">Показувати до 30 днів</span>
          <IosToggle
            checked={!customActive && publishedWithinDays === "30"}
            disabled={customActive}
            aria-label="Показувати оголошення до 30 днів"
            onChange={checked => setWithinDaysToggle("30", checked)}
          />
        </div>
      </div>

      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[13px] font-medium text-ink">Дата публікації</p>
          <p className="mt-0.5 text-[11px] text-muted">
            Швидкі періоди або свій діапазон з календарем і часом
          </p>
        </div>
        {summary ? (
          <button
            type="button"
            onClick={clearAll}
            className="shrink-0 rounded-full border border-border px-2.5 py-1 text-[11px] font-medium text-muted transition-colors hover:border-red-300 hover:text-red-600"
          >
            Скинути
          </button>
        ) : null}
      </div>

      {summary ? (
        <div className="rounded-lg border border-emerald/20 bg-emerald/[0.06] px-3 py-2 text-[12px] font-medium text-emerald-dark">
          {summary}
        </div>
      ) : null}

      <div className="flex flex-wrap gap-1.5">
        {PUBLISHED_PRESET_OPTIONS.map(option => {
          const active = !customActive && publishedWithinDays === option.value;
          return (
            <button
              key={option.value}
              type="button"
              onClick={() => selectPreset(option.value)}
              className={cn(
                "rounded-full border px-2.5 py-1 text-[11px] font-medium transition-colors",
                active
                  ? "border-emerald bg-emerald text-white"
                  : "border-border bg-white text-muted hover:border-emerald/40",
              )}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <div className="rounded-xl border border-border/70 bg-white p-3">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <p className="text-[12px] font-semibold text-ink">Свій період</p>
          <div className="flex flex-wrap gap-1.5">
            <button
              type="button"
              onClick={() => setQuickRange(0)}
              className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted hover:border-emerald/40"
            >
              Сьогодні
            </button>
            <button
              type="button"
              onClick={() => setQuickRange(1)}
              className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted hover:border-emerald/40"
            >
              Вчора
            </button>
            <button
              type="button"
              onClick={() => setQuickRange(7)}
              className="rounded-full border border-border px-2 py-0.5 text-[10px] font-medium text-muted hover:border-emerald/40"
            >
              7 днів
            </button>
          </div>
        </div>

        <div className="mb-3 grid grid-cols-2 gap-2">
          {(["from", "to"] as const).map(field => {
            const value = field === "from" ? publishedFrom : publishedTo;
            const active = activeField === field;
            return (
              <button
                key={field}
                type="button"
                onClick={() => setActiveField(field)}
                className={cn(
                  "rounded-xl border px-3 py-2 text-left transition-colors",
                  active
                    ? "border-emerald bg-emerald/5"
                    : "border-border bg-surface/40 hover:border-emerald/30",
                )}
              >
                <span className="block text-[10px] font-semibold uppercase tracking-wide text-muted">
                  {field === "from" ? "Від" : "До"}
                </span>
                <span className="mt-0.5 block text-[12px] font-medium text-ink">
                  {value ? formatPublishedDateTimeLabel(value) : "Оберіть дату"}
                </span>
              </button>
            );
          })}
        </div>

        <div className="mb-3 grid grid-cols-2 gap-2">
          <label className="space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">Час від</span>
            <input
              type="time"
              value={publishedFrom ? publishedFrom.slice(11, 16) : ""}
              onChange={event => {
                if (!publishedFrom) return;
                const datePart = publishedFrom.slice(0, 10);
                updateCustom(`${datePart}T${event.target.value}`, publishedTo);
              }}
              disabled={!publishedFrom}
              className="w-full rounded-lg border border-border bg-white px-2.5 py-2 text-[13px] text-ink disabled:opacity-50"
            />
          </label>
          <label className="space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">Час до</span>
            <input
              type="time"
              value={publishedTo ? publishedTo.slice(11, 16) : ""}
              onChange={event => {
                if (!publishedTo) return;
                const datePart = publishedTo.slice(0, 10);
                updateCustom(publishedFrom, `${datePart}T${event.target.value}`);
              }}
              disabled={!publishedTo}
              className="w-full rounded-lg border border-border bg-white px-2.5 py-2 text-[13px] text-ink disabled:opacity-50"
            />
          </label>
        </div>

        <div className="mb-2 flex items-center justify-between">
          <button
            type="button"
            onClick={() => shiftMonth(-1)}
            className="rounded-lg border border-border px-2.5 py-1 text-[12px] text-muted hover:border-emerald/40"
            aria-label="Попередній місяць"
          >
            ‹
          </button>
          <span className="text-[13px] font-semibold text-ink">
            {PUBLISHED_MONTHS[viewMonth.month]} {viewMonth.year}
          </span>
          <button
            type="button"
            onClick={() => shiftMonth(1)}
            className="rounded-lg border border-border px-2.5 py-1 text-[12px] text-muted hover:border-emerald/40"
            aria-label="Наступний місяць"
          >
            ›
          </button>
        </div>

        <div className="mb-1 grid grid-cols-7 gap-1">
          {PUBLISHED_WEEKDAYS.map(day => (
            <div
              key={day}
              className="py-1 text-center text-[10px] font-semibold uppercase text-muted"
            >
              {day}
            </div>
          ))}
        </div>

        <div className="grid grid-cols-7 gap-1">
          {calendarDays.map((day, index) => {
            if (!day) return <div key={`empty-${index}`} className="h-9" />;
            const fromDate = parseLocalDateTime(publishedFrom);
            const toDate = parseLocalDateTime(publishedTo);
            const selected =
              sameCalendarDay(day, fromDate) || sameCalendarDay(day, toDate);
            const inRange = isDayInPublishedRange(day, publishedFrom, publishedTo);
            const isToday = sameCalendarDay(day, new Date());
            return (
              <button
                key={day.toISOString()}
                type="button"
                onClick={() => handleDayClick(day)}
                className={cn(
                  "h-9 rounded-lg text-[12px] font-medium transition-colors",
                  selected
                    ? "bg-emerald text-white"
                    : inRange
                      ? "bg-emerald/15 text-emerald-dark"
                      : "text-ink hover:bg-surface",
                  isToday && !selected && "ring-1 ring-emerald/30",
                )}
              >
                {day.getDate()}
              </button>
            );
          })}
        </div>

        <div className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-2">
          <label className="space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">
              Дата і час від
            </span>
            <input
              type="datetime-local"
              value={publishedFrom}
              onChange={event => updateCustom(event.target.value, publishedTo)}
              className="w-full rounded-lg border border-border bg-white px-2.5 py-2 text-[13px] text-ink"
            />
          </label>
          <label className="space-y-1">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted">
              Дата і час до
            </span>
            <input
              type="datetime-local"
              value={publishedTo}
              onChange={event => updateCustom(publishedFrom, event.target.value)}
              className="w-full rounded-lg border border-border bg-white px-2.5 py-2 text-[13px] text-ink"
            />
          </label>
        </div>
      </div>
    </div>
  );
}
