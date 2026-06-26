export type ExportFormat = "csv" | "excel";

export type ExportListing = {
  id?: string;
  title: string;
  year: number;
  mileage: number;
  price: number;
  region: string;
  src: string;
  fuel?: string;
  trans?: string;
  desc?: string;
  time?: string;
  risk?: string;
  url?: string;
};

const RISK_LABELS: Record<string, string> = {
  low: "Брати",
  medium: "Торгуватись",
  high: "Пропустити",
};

const COLUMNS: { key: keyof ExportListing | "riskLabel"; header: string }[] = [
  { key: "title", header: "Назва" },
  { key: "year", header: "Рік" },
  { key: "mileage", header: "Пробіг, км" },
  { key: "price", header: "Ціна, грн" },
  { key: "region", header: "Регіон" },
  { key: "fuel", header: "Паливо" },
  { key: "trans", header: "КПП" },
  { key: "src", header: "Джерело" },
  { key: "riskLabel", header: "Оцінка" },
  { key: "time", header: "Час" },
  { key: "desc", header: "Опис" },
  { key: "url", header: "Посилання" },
];

function cellValue(item: ExportListing, key: typeof COLUMNS[number]["key"]): string {
  if (key === "riskLabel") {
    return item.risk ? RISK_LABELS[item.risk] ?? item.risk : "";
  }
  const value = item[key as keyof ExportListing];
  if (value == null) return "";
  return String(value);
}

function escapeCsv(value: string): string {
  if (/[",\n\r]/.test(value)) {
    return `"${value.replace(/"/g, '""')}"`;
  }
  return value;
}

function escapeXml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function download(content: string, filename: string, mime: string) {
  const blob = new Blob([content], { type: mime });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

function buildCsv(items: ExportListing[]): string {
  const header = COLUMNS.map(c => escapeCsv(c.header)).join(",");
  const rows = items.map(item =>
    COLUMNS.map(c => escapeCsv(cellValue(item, c.key))).join(","),
  );
  return `\uFEFF${[header, ...rows].join("\r\n")}`;
}

function buildExcelXml(items: ExportListing[]): string {
  const headerRow = COLUMNS.map(c =>
    `<Cell><Data ss:Type="String">${escapeXml(c.header)}</Data></Cell>`,
  ).join("");

  const dataRows = items.map(item => {
    const cells = COLUMNS.map(c => {
      const raw = cellValue(item, c.key);
      const isNumber = c.key === "year" || c.key === "mileage" || c.key === "price";
      const type = isNumber && raw !== "" ? "Number" : "String";
      return `<Cell><Data ss:Type="${type}">${escapeXml(raw)}</Data></Cell>`;
    }).join("");
    return `<Row>${cells}</Row>`;
  }).join("");

  return `<?xml version="1.0"?>
<?mso-application progid="Excel.Sheet"?>
<Workbook xmlns="urn:schemas-microsoft-com:office:spreadsheet"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:x="urn:schemas-microsoft-com:office:excel"
 xmlns:ss="urn:schemas-microsoft-com:office:spreadsheet">
 <Worksheet ss:Name="Оголошення">
  <Table>
   <Row>${headerRow}</Row>
   ${dataRows}
  </Table>
 </Worksheet>
</Workbook>`;
}

export function exportListings(
  items: ExportListing[],
  format: ExportFormat,
  filenameBase: string,
) {
  if (items.length === 0) return false;

  const safeName = filenameBase.replace(/[^\w\u0400-\u04FF\-]+/g, "_").slice(0, 80) || "export";

  if (format === "csv") {
    download(buildCsv(items), `${safeName}.csv`, "text/csv;charset=utf-8");
    return true;
  }

  download(
    buildExcelXml(items),
    `${safeName}.xls`,
    "application/vnd.ms-excel",
  );
  return true;
}
