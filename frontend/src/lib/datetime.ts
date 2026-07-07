export const KYIV_TIME_ZONE = "Europe/Kyiv";

const dateTimeFormatter = new Intl.DateTimeFormat("uk-UA", {
  timeZone: KYIV_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
  hour: "2-digit",
  minute: "2-digit",
  second: "2-digit",
});

const dateFormatter = new Intl.DateTimeFormat("uk-UA", {
  timeZone: KYIV_TIME_ZONE,
  day: "2-digit",
  month: "2-digit",
  year: "numeric",
});

function toDate(value: string | Date | number | null | undefined): Date | null {
  if (value == null || value === "") return null;
  const date = value instanceof Date ? value : new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function formatKyivDateTime(value: string | Date | number | null | undefined): string {
  const date = toDate(value);
  return date ? dateTimeFormatter.format(date) : "—";
}

export function formatKyivDate(value: string | Date | number | null | undefined): string {
  const date = toDate(value);
  return date ? dateFormatter.format(date) : "—";
}
