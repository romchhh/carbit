import {
  convertPrice,
  formatListingPrice,
  nativeAmountFromSourceData,
  resolveDisplayCurrency,
  resolveListingCurrency,
  type DisplayCurrency,
} from "@/lib/display-currency";
import {
  formatListingAccident,
  resolveListingAccidentHad,
} from "@/lib/listing-accident";
import {
  formatEngineVolume,
  resolveListingEngineVolume,
  resolveListingMileage,
} from "@/lib/listing-specs";
import { listingSourceLinks } from "@/components/listings/SourceLinks";
import { resolveListingVin } from "@/lib/vin-check";
import { formatMileage, publishedAgoLabel } from "@/lib/utils";
import type { Listing } from "@/types/api";

export type CompareRow = {
  key: string;
  label: string;
  values: string[];
  highlightIndexes?: number[];
  /** Індекси комірок з негативним акцентом (напр. був у ДТП). */
  dangerIndexes?: number[];
  /** Позитивний акцент (напр. ДТП не вказано / не був). */
  safeIndexes?: number[];
};

/** Рядки, які лишаються в таблиці навіть без даних або при однакових значеннях. */
const ALWAYS_VISIBLE_COMPARE_ROW_KEYS = new Set(["accident"]);

function sourceLabel(source: string): string {
  const key = (source || "").trim().toLowerCase();
  if (key === "olx") return "OLX";
  if (key === "auto_ria") return "AUTO.RIA";
  if (key === "imperiya") return "Імперія Авто";
  if (key === "udrive") return "uDrive";
  if (key === "telegram") return "Telegram";
  return source || "—";
}

function sellerLabel(sellerType: string): string {
  if (sellerType === "dealer") return "Автосалон";
  return "Приват";
}

function normalizeCell(value: string): string {
  return value.trim().toLowerCase().replace(/\s+/g, " ");
}

function isEmptyCompareValue(value: string): boolean {
  const normalized = normalizeCell(value === "—" ? "" : value);
  return !normalized;
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

function readAutoRiaText(listing: Listing, ...paths: string[]): string {
  const sd = asRecord(listing.source_data);
  const auto = asRecord(sd.autoData);
  const mainParams = asRecord(sd.mainParams);
  const color = asRecord(sd.color);
  for (const path of paths) {
    if (path === "color.name") {
      const v = color.name;
      if (typeof v === "string" && v.trim()) return v.trim();
    }
    const v = auto[path] ?? mainParams[path] ?? sd[path];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "—";
}

function comparePriceUah(listing: Listing, displayCurrency: DisplayCurrency): number | null {
  const native = nativeAmountFromSourceData(listing.source_data, displayCurrency);
  const from = resolveListingCurrency(listing.currency);
  const raw = native != null && native > 0 ? native : Number(listing.price) || 0;
  if (raw <= 0) return null;
  const converted = convertPrice(raw, from, displayCurrency);
  return converted > 0 ? converted : null;
}

function minValueIndexes(values: (number | null)[], positiveOnly = false): number[] {
  const entries = values
    .map((value, index) => ({ value, index }))
    .filter(entry => entry.value != null && (!positiveOnly || entry.value > 0));
  if (entries.length < 2) return [];
  const min = Math.min(...entries.map(entry => entry.value!));
  return entries.filter(entry => entry.value === min).map(entry => entry.index);
}

function withHighlights(
  row: Omit<CompareRow, "highlightIndexes" | "dangerIndexes">,
  indexes: number[],
): CompareRow {
  return indexes.length ? { ...row, highlightIndexes: indexes } : row;
}

function withDanger(
  row: Omit<CompareRow, "highlightIndexes" | "dangerIndexes">,
  indexes: number[],
): CompareRow {
  return indexes.length ? { ...row, dangerIndexes: indexes } : row;
}

/** Ховає рядки, де в усіх авто значення порожні («—»), крім завжди видимих. */
export function filterEmptyRows(rows: CompareRow[]): CompareRow[] {
  return rows.filter(
    row =>
      ALWAYS_VISIBLE_COMPARE_ROW_KEYS.has(row.key) ||
      !row.values.every(isEmptyCompareValue),
  );
}

export function buildCompareRows(
  listings: Listing[],
  displayCurrency?: DisplayCurrency,
  options?: { includePremiumFields?: boolean },
): CompareRow[] {
  const currency = resolveDisplayCurrency(displayCurrency);
  const includePremium = Boolean(options?.includePremiumFields);

  const row = (key: string, label: string, values: string[]): CompareRow => ({
    key,
    label,
    values,
  });

  const priceValues = listings.map(l =>
    formatListingPrice(Number(l.price) || 0, l.currency, currency, l.source_data),
  );
  const priceNums = listings.map(l => comparePriceUah(l, currency));
  const mileageNums = listings.map(l => {
    const km = resolveListingMileage(l);
    return km != null && km > 0 ? km : null;
  });
  const accidentFlags = listings.map(resolveListingAccidentHad);

  const rows: CompareRow[] = [
    row(
      "brand_model",
      "Марка / модель",
      listings.map(l =>
        [l.brand, l.model].filter(Boolean).join(" ").trim() || l.title || "—",
      ),
    ),
    row("year", "Рік", listings.map(l => (l.year > 0 ? String(l.year) : "—"))),
    withHighlights(
      { key: "price", label: "Ціна", values: priceValues },
      minValueIndexes(priceNums, true),
    ),
    withHighlights(
      {
        key: "mileage",
        label: "Пробіг",
        values: listings.map(l => {
          const km = resolveListingMileage(l);
          return km != null && km > 0 ? formatMileage(km) : "—";
        }),
      },
      minValueIndexes(mileageNums, true),
    ),
    row(
      "fuel",
      "Паливо",
      listings.map(l => (l.fuel ? l.fuel.split(",")[0]?.trim() || l.fuel : "—")),
    ),
    row(
      "transmission",
      "КПП",
      listings.map(l => l.transmission || "—"),
    ),
    row(
      "engine",
      "Обʼєм двигуна",
      listings.map(l => {
        const vol = resolveListingEngineVolume(l);
        return vol != null ? formatEngineVolume(vol) : "—";
      }),
    ),
    withDanger(
      {
        key: "accident",
        label: "ДТП",
        values: accidentFlags.map(formatListingAccident),
        safeIndexes: accidentFlags
          .map((had, index) => (had !== true ? index : -1))
          .filter(index => index >= 0),
      },
      accidentFlags
        .map((had, index) => (had === true ? index : -1))
        .filter(index => index >= 0),
    ),
  ];

  if (includePremium) {
    rows.push(
      row("color", "Колір", listings.map(l => readAutoRiaText(l, "color.name"))),
      row(
        "equipment",
        "Комплектація",
        listings.map(l => readAutoRiaText(l, "equipmentName")),
      ),
      row(
        "drive",
        "Привід",
        listings.map(l => {
          const fromRia = readAutoRiaText(l, "driveName", "drive");
          return fromRia !== "—" ? fromRia : "—";
        }),
      ),
      row(
        "body",
        "Кузов",
        listings.map(l => {
          const sd = asRecord(l.source_data);
          const auto = asRecord(sd.autoData);
          const mainParams = asRecord(sd.mainParams);
          for (const raw of [sd.subCategoryName, auto.bodyName, mainParams.body]) {
            if (typeof raw === "string" && raw.trim()) return raw.trim();
          }
          return "—";
        }),
      ),
    );
  }

  rows.push(
    row(
      "region",
      "Регіон",
      listings.map(l => l.region?.split(",")[0]?.trim() || l.region || "—"),
    ),
    row(
      "seller",
      "Продавець",
      listings.map(l => sellerLabel(l.seller_type)),
    ),
    row(
      "vin",
      "VIN",
      listings.map(l => resolveListingVin(l) || "—"),
    ),
    row(
      "sources",
      "Джерела",
      listings.map(l => {
        const links = listingSourceLinks(l);
        if (links.length === 0) return sourceLabel(l.source);
        return links.map(s => sourceLabel(s.source)).join(", ");
      }),
    ),
    row(
      "published",
      "Опубліковано",
      listings.map(l => (l.published_at ? publishedAgoLabel(l.published_at) || l.published_at : "—")),
    ),
  );

  return filterEmptyRows(rows);
}

/** Лишає рядки, де значення відрізняються (як «Відмінні» на Hotline). */
export function filterDifferentRows(rows: CompareRow[]): CompareRow[] {
  return rows.filter(({ key, values }) => {
    if (ALWAYS_VISIBLE_COMPARE_ROW_KEYS.has(key)) return true;
    const meaningful = values.map(v => normalizeCell(v === "—" ? "" : v));
    const nonEmpty = meaningful.filter(Boolean);
    if (nonEmpty.length <= 1) return nonEmpty.length === 1;
    return new Set(nonEmpty).size > 1;
  });
}
