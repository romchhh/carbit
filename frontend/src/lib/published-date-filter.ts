import type { PublishedWithinDaysValue } from "@/lib/search-catalog";
import { PUBLISHED_WITHIN_OPTIONS, publishedWithinDaysLabel } from "@/lib/search-catalog";
import type { SearchFreshness } from "@/lib/search-preview";

export function pad2(value: number): string {
  return String(value).padStart(2, "0");
}

export function formatLocalDateTime(date: Date): string {
  return `${date.getFullYear()}-${pad2(date.getMonth() + 1)}-${pad2(date.getDate())}T${pad2(date.getHours())}:${pad2(date.getMinutes())}`;
}

export function parseLocalDateTime(value: string): Date | null {
  if (!value?.trim()) return null;
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

export function toLocalDateTimeInput(value: string | Date): string {
  const parsed = value instanceof Date ? value : parseLocalDateTime(String(value));
  if (!parsed) return "";
  return formatLocalDateTime(parsed);
}

export function formatPublishedDateTimeLabel(value: string): string {
  const parsed = parseLocalDateTime(value);
  if (!parsed) return "";
  return parsed.toLocaleString("uk-UA", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function normalizePublishedRange(from: string, to: string): { from: string; to: string } {
  const start = parseLocalDateTime(from);
  const end = parseLocalDateTime(to);
  if (!start || !end) return { from, to };
  if (start.getTime() <= end.getTime()) return { from, to };
  return { from: to, to: from };
}

export function hasCustomPublishedRange(from: string, to: string): boolean {
  return Boolean(from.trim() || to.trim());
}

export function isPublishedFilterActive(
  publishedWithinDays: PublishedWithinDaysValue,
  publishedFrom: string,
  publishedTo: string,
): boolean {
  return Boolean(publishedWithinDays || hasCustomPublishedRange(publishedFrom, publishedTo));
}

export function formatPublishedFilterSummary(
  publishedWithinDays: PublishedWithinDaysValue,
  publishedFrom: string,
  publishedTo: string,
  freshness: SearchFreshness = "all",
): string {
  if (freshness === "new") {
    return "Тільки свіжі";
  }
  if (hasCustomPublishedRange(publishedFrom, publishedTo)) {
    const fromLabel = publishedFrom ? formatPublishedDateTimeLabel(publishedFrom) : "…";
    const toLabel = publishedTo ? formatPublishedDateTimeLabel(publishedTo) : "…";
    return `${fromLabel} — ${toLabel}`;
  }
  if (publishedWithinDays) {
    return publishedWithinDaysLabel(publishedWithinDays);
  }
  return "";
}

export function isListingAgeFilterActive(
  publishedWithinDays: PublishedWithinDaysValue,
  publishedFrom: string,
  publishedTo: string,
  freshness: SearchFreshness = "all",
): boolean {
  return freshness === "new" || isPublishedFilterActive(publishedWithinDays, publishedFrom, publishedTo);
}

export function getCalendarDays(year: number, month: number): (Date | null)[] {
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const cells: (Date | null)[] = Array.from({ length: startOffset }, () => null);
  for (let day = 1; day <= daysInMonth; day += 1) {
    cells.push(new Date(year, month, day));
  }
  while (cells.length % 7 !== 0) cells.push(null);
  return cells;
}

export function sameCalendarDay(a: Date | null, b: Date | null): boolean {
  if (!a || !b) return false;
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  );
}

export function isDayInPublishedRange(
  day: Date,
  from: string,
  to: string,
): boolean {
  const start = parseLocalDateTime(from);
  const end = parseLocalDateTime(to);
  if (!start || !end) return false;
  const dayStart = new Date(day.getFullYear(), day.getMonth(), day.getDate()).getTime();
  const rangeStart = new Date(start.getFullYear(), start.getMonth(), start.getDate()).getTime();
  const rangeEnd = new Date(end.getFullYear(), end.getMonth(), end.getDate()).getTime();
  const min = Math.min(rangeStart, rangeEnd);
  const max = Math.max(rangeStart, rangeEnd);
  return dayStart >= min && dayStart <= max;
}

export function applyCalendarDay(
  day: Date,
  field: "from" | "to",
  currentFrom: string,
  currentTo: string,
): { from: string; to: string } {
  const existing = field === "from" ? parseLocalDateTime(currentFrom) : parseLocalDateTime(currentTo);
  const hours = existing?.getHours() ?? (field === "from" ? 0 : 23);
  const minutes = existing?.getMinutes() ?? (field === "from" ? 0 : 59);
  const next = formatLocalDateTime(
    new Date(day.getFullYear(), day.getMonth(), day.getDate(), hours, minutes),
  );
  const patch =
    field === "from"
      ? { from: next, to: currentTo }
      : { from: currentFrom, to: next };
  return normalizePublishedRange(patch.from, patch.to);
}

export const PUBLISHED_MONTHS = [
  "Січень",
  "Лютий",
  "Березень",
  "Квітень",
  "Травень",
  "Червень",
  "Липень",
  "Серпень",
  "Вересень",
  "Жовтень",
  "Листопад",
  "Грудень",
] as const;

export const PUBLISHED_WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"] as const;

export const PUBLISHED_PRESET_OPTIONS = PUBLISHED_WITHIN_OPTIONS.filter(option => option.value);
