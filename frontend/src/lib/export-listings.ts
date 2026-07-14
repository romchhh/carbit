import {
  convertPrice,
  currencySuffix,
  resolveDisplayCurrency,
  type DisplayCurrency,
} from "@/lib/display-currency";
import type { Listing } from "@/types/api";

export type ExportFormat = "csv" | "excel" | "html";

export type ExportListing = {
  id?: string;
  title: string;
  brand?: string;
  model?: string;
  year: number;
  mileage: number;
  price: number;
  currency?: string;
  region: string;
  src: string;
  fuel?: string;
  trans?: string;
  desc?: string;
  time?: string;
  risk?: string;
  url?: string;
  vin?: string;
  sellerType?: string;
  publishedAt?: string;
  refreshedAt?: string;
  foundAt?: string;
  isNew?: boolean;
  images?: string[];
  photo?: string;
  sources?: string;
  altUrls?: string;
};

const RISK_LABELS: Record<string, string> = {
  low: "Брати",
  medium: "Торгуватись",
  high: "Пропустити",
};

const SELLER_LABELS: Record<string, string> = {
  private: "Приватна особа",
  dealer: "Автосалон",
  company: "Компанія",
};

type ColumnKey =
  | keyof ExportListing
  | "row"
  | "riskLabel"
  | "priceDisplay"
  | "mileageDisplay"
  | "photoHtml"
  | "photosCount"
  | "allPhotos"
  | "isNewLabel"
  | "sellerLabel"
  | "publishedLabel"
  | "refreshedLabel";

type Column = {
  key: ColumnKey;
  header: string;
  width?: number;
  align?: "left" | "center" | "right";
};

function sourceLabel(source: string): string {
  const key = (source || "").trim().toLowerCase();
  if (key === "olx") return "OLX";
  if (key === "auto_ria" || key === "auto.ria") return "AUTO.RIA";
  if (key === "telegram") return "Telegram";
  return source || "";
}

function sellerLabel(value?: string): string {
  if (!value) return "";
  return SELLER_LABELS[value] ?? value;
}

function formatDateTime(value?: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("uk-UA", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Kyiv",
  }).format(date);
}

function formatNumber(value: number): string {
  return new Intl.NumberFormat("uk-UA").format(value);
}

export function listingToExportItem(listing: Listing): ExportListing {
  const images = Array.isArray(listing.images) ? listing.images.filter(Boolean) : [];
  const alt = listing.alternate_sources ?? [];
  const sources = [sourceLabel(listing.source), ...alt.map(a => sourceLabel(a.source))]
    .filter(Boolean)
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .join(", ");
  const altUrls = alt
    .map(a => a.url)
    .filter(Boolean)
    .join(" | ");

  return {
    id: listing.id,
    title: listing.title || `${listing.brand} ${listing.model}`.trim(),
    brand: listing.brand || "",
    model: listing.model || "",
    year: listing.year || 0,
    mileage: listing.mileage || 0,
    price: listing.price || 0,
    currency: listing.currency,
    region: listing.region || "",
    src: sourceLabel(listing.source),
    fuel: listing.fuel || "",
    trans: listing.transmission || "",
    desc: listing.description ?? "",
    url: listing.url || "",
    vin: listing.vin ?? "",
    sellerType: listing.seller_type || "",
    publishedAt: listing.published_at,
    refreshedAt: listing.refreshed_at ?? "",
    foundAt: listing.found_at,
    isNew: Boolean(listing.is_new),
    images,
    photo: images[0] || "",
    sources,
    altUrls,
  };
}

export function listingsToExportItems(items: Listing[]): ExportListing[] {
  return items.map(listingToExportItem);
}

function columnsFor(currency: DisplayCurrency): Column[] {
  return [
    { key: "row", header: "№", width: 40, align: "center" },
    { key: "photoHtml", header: "Фото", width: 120, align: "center" },
    { key: "title", header: "Назва", width: 220 },
    { key: "brand", header: "Марка", width: 90 },
    { key: "model", header: "Модель", width: 100 },
    { key: "year", header: "Рік", width: 55, align: "center" },
    { key: "mileageDisplay", header: "Пробіг", width: 90, align: "right" },
    { key: "priceDisplay", header: `Ціна (${currencySuffix(currency)})`, width: 100, align: "right" },
    { key: "fuel", header: "Паливо", width: 80 },
    { key: "trans", header: "КПП", width: 80 },
    { key: "region", header: "Регіон", width: 110 },
    { key: "sellerLabel", header: "Продавець", width: 110 },
    { key: "vin", header: "VIN", width: 150 },
    { key: "sources", header: "Джерела", width: 120 },
    { key: "isNewLabel", header: "Нове", width: 55, align: "center" },
    { key: "publishedLabel", header: "Опубліковано", width: 120 },
    { key: "refreshedLabel", header: "Оновлено", width: 120 },
    { key: "riskLabel", header: "Оцінка", width: 90 },
    { key: "photosCount", header: "Фото, шт", width: 70, align: "center" },
    { key: "allPhotos", header: "Усі фото (посилання)", width: 220 },
    { key: "desc", header: "Опис", width: 280 },
    { key: "url", header: "Посилання", width: 200 },
    { key: "altUrls", header: "Інші джерела", width: 200 },
  ];
}

function cellValue(
  item: ExportListing,
  key: ColumnKey,
  currency: DisplayCurrency,
  rowIndex: number,
): string {
  switch (key) {
    case "row":
      return String(rowIndex + 1);
    case "riskLabel":
      return item.risk ? RISK_LABELS[item.risk] ?? item.risk : "";
    case "sellerLabel":
      return sellerLabel(item.sellerType);
    case "priceDisplay": {
      const amount = convertPrice(Number(item.price) || 0, item.currency, currency);
      return formatNumber(amount);
    }
    case "mileageDisplay":
      return item.mileage != null ? formatNumber(Number(item.mileage) || 0) : "";
    case "photosCount":
      return String((item.images?.length || (item.photo ? 1 : 0)) || 0);
    case "allPhotos":
      return (item.images?.length ? item.images : item.photo ? [item.photo] : []).join(" | ");
    case "photoHtml":
      return item.photo || item.images?.[0] || "";
    case "isNewLabel":
      return item.isNew ? "Так" : "";
    case "publishedLabel":
      return formatDateTime(item.publishedAt) || item.time || "";
    case "refreshedLabel":
      return formatDateTime(item.refreshedAt);
    case "sources":
      return item.sources || item.src || "";
    case "price":
      return String(convertPrice(Number(item.price) || 0, item.currency, currency));
    default: {
      const value = item[key as keyof ExportListing];
      if (value == null || value === false) return "";
      if (typeof value === "boolean") return value ? "Так" : "";
      if (Array.isArray(value)) return value.join(" | ");
      return String(value);
    }
  }
}

function escapeCsv(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function download(content: string, filename: string, mime: string) {
  downloadBlob(new Blob([content], { type: mime }), filename);
}

function buildCsv(items: ExportListing[], currency: DisplayCurrency): string {
  const columns = columnsFor(currency).filter(c => c.key !== "photoHtml");
  const header = columns.map(c => escapeCsv(c.header)).join(";");
  const rows = items.map((item, index) =>
    columns.map(c => escapeCsv(cellValue(item, c.key, currency, index))).join(";"),
  );
  return `\uFEFF${[header, ...rows].join("\r\n")}`;
}

function photoCellHtml(url: string): string {
  if (!url) {
    return `<div style="width:96px;height:72px;background:#F3F4F6;border-radius:6px;color:#9CA3AF;font-size:11px;display:flex;align-items:center;justify-content:center;">Немає</div>`;
  }
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener"><img src="${escapeHtml(url)}" width="96" height="72" style="width:96px;height:72px;object-fit:cover;border-radius:6px;border:1px solid #E5E7EB;display:block;" /></a>`;
}

function linkCellHtml(url: string, label?: string): string {
  if (!url) return "";
  const text = label || url;
  return `<a href="${escapeHtml(url)}" target="_blank" rel="noopener" style="color:#0F766E;text-decoration:none;">${escapeHtml(text)}</a>`;
}

function richCellHtml(
  item: ExportListing,
  key: ColumnKey,
  currency: DisplayCurrency,
  rowIndex: number,
): string {
  if (key === "photoHtml") {
    return photoCellHtml(item.photo || item.images?.[0] || "");
  }
  if (key === "url") {
    return linkCellHtml(item.url || "", "Відкрити оголошення");
  }
  if (key === "allPhotos") {
    const photos = item.images?.length ? item.images : item.photo ? [item.photo] : [];
    if (!photos.length) return "";
    return photos
      .map((url, i) => linkCellHtml(url, `Фото ${i + 1}`))
      .join("<br/>");
  }
  if (key === "altUrls") {
    if (!item.altUrls) return "";
    return item.altUrls
      .split(" | ")
      .filter(Boolean)
      .map((url, i) => linkCellHtml(url, `Джерело ${i + 1}`))
      .join("<br/>");
  }
  if (key === "desc") {
    const text = cellValue(item, key, currency, rowIndex);
    return `<div style="max-width:280px;white-space:pre-wrap;line-height:1.35;">${escapeHtml(text)}</div>`;
  }
  return escapeHtml(cellValue(item, key, currency, rowIndex));
}

function buildRichTableHtml(
  items: ExportListing[],
  currency: DisplayCurrency,
  filenameBase: string,
  forExcel: boolean,
): string {
  const columns = columnsFor(currency);
  const generatedAt = formatDateTime(new Date().toISOString());
  const title = filenameBase || "Carbit export";

  const colGroup = columns
    .map(c => `<col style="width:${c.width ?? 100}px;" />`)
    .join("");

  const headerCells = columns
    .map(
      c =>
        `<th style="background:#0F766E;color:#ffffff;font-weight:700;font-size:12px;padding:10px 8px;border:1px solid #0D9488;text-align:${c.align || "left"};white-space:nowrap;vertical-align:middle;">${escapeHtml(c.header)}</th>`,
    )
    .join("");

  const bodyRows = items
    .map((item, index) => {
      const bg = index % 2 === 0 ? "#FFFFFF" : "#F8FAFC";
      const cells = columns
        .map(c => {
          const align = c.align || "left";
          const isNum =
            c.key === "year" ||
            c.key === "priceDisplay" ||
            c.key === "mileageDisplay" ||
            c.key === "photosCount" ||
            c.key === "row";
          const mso = isNum ? "mso-number-format:'0';" : "mso-number-format:'\\@';";
          return `<td style="background:${bg};padding:8px;border:1px solid #E5E7EB;font-size:12px;color:#111827;vertical-align:middle;text-align:${align};${mso}">${richCellHtml(item, c.key, currency, index)}</td>`;
        })
        .join("");
      return `<tr>${cells}</tr>`;
    })
    .join("\n");

  const excelMeta = forExcel
    ? `<!--[if gte mso 9]><xml>
 <x:ExcelWorkbook>
  <x:ExcelWorksheets>
   <x:ExcelWorksheet>
    <x:Name>Оголошення</x:Name>
    <x:WorksheetOptions>
     <x:FreezePanes/>
     <x:FrozenNoSplit/>
     <x:SplitHorizontal>1</x:SplitHorizontal>
     <x:TopRowBottomPane>1</x:TopRowBottomPane>
     <x:ActivePane>2</x:ActivePane>
    </x:WorksheetOptions>
   </x:ExcelWorksheet>
  </x:ExcelWorksheets>
 </x:ExcelWorkbook>
</xml><![endif]-->`
    : "";

  return `<!DOCTYPE html>
<html xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns="http://www.w3.org/TR/REC-html40">
<head>
<meta charset="UTF-8" />
<meta http-equiv="content-type" content="text/html; charset=UTF-8" />
<title>${escapeHtml(title)}</title>
${excelMeta}
<style>
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Arial, sans-serif; margin: 24px; color: #111827; background: #F8FAFC; }
  .wrap { max-width: 100%; background: #fff; border: 1px solid #E5E7EB; border-radius: 16px; overflow: hidden; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.06); }
  .head { padding: 18px 20px; border-bottom: 1px solid #E5E7EB; background: linear-gradient(180deg, #FFFFFF, #F8FAFC); }
  .head h1 { margin: 0; font-size: 20px; font-weight: 800; letter-spacing: -0.02em; }
  .head p { margin: 6px 0 0; font-size: 13px; color: #6B7280; }
  .scroll { overflow-x: auto; }
  table { border-collapse: collapse; width: 100%; min-width: 1400px; table-layout: fixed; }
  th, td { word-wrap: break-word; overflow-wrap: anywhere; }
  img { max-width: 96px; }
</style>
</head>
<body>
  <div class="wrap">
    <div class="head">
      <h1>${escapeHtml(title)}</h1>
      <p>Carbit · ${items.length} оголошень · ${escapeHtml(generatedAt)} · ціни в ${escapeHtml(currencySuffix(currency))}</p>
    </div>
    <div class="scroll">
      <table>
        <colgroup>${colGroup}</colgroup>
        <thead><tr>${headerCells}</tr></thead>
        <tbody>
          ${bodyRows}
        </tbody>
      </table>
    </div>
  </div>
</body>
</html>`;
}

export function exportListings(
  items: ExportListing[],
  format: ExportFormat,
  filenameBase: string,
  displayCurrency?: string | null,
) {
  if (items.length === 0) return false;

  const currency = resolveDisplayCurrency(displayCurrency);
  const safeName = filenameBase.replace(/[^\w\u0400-\u04FF\-]+/g, "_").slice(0, 80) || "export";

  if (format === "csv") {
    download(buildCsv(items, currency), `${safeName}.csv`, "text/csv;charset=utf-8");
    return true;
  }

  if (format === "html") {
    download(
      buildRichTableHtml(items, currency, safeName, false),
      `${safeName}.html`,
      "text/html;charset=utf-8",
    );
    return true;
  }

  // Excel: HTML-таблиця з фото — відкривається в Microsoft Excel / Numbers / LibreOffice
  download(
    buildRichTableHtml(items, currency, safeName, true),
    `${safeName}.xls`,
    "application/vnd.ms-excel;charset=utf-8",
  );
  return true;
}
