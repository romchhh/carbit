export type AutoRiaDetailRow = {
  label: string;
  value: string;
  kind?: "text" | "link" | "color";
  href?: string;
  colorHex?: string;
};

export type AutoRiaDetailSection = {
  title: string;
  rows: AutoRiaDetailRow[];
};

const HIDDEN_SECTIONS = new Set([
  "photoData",
  "infotechReport",
  "_fotos",
  "badges",
  "optionStyles",
  "userPhoneData",
]);

const HIDDEN_FIELDS = new Set([
  "prices",
  "vinSvg",
  "linkToView",
  "dontComment",
  "sendComments",
  "canSetSpecificPhoneToAdvert",
  "userHideADSStatus",
  "chipsCount",
  "isAutoAddedByPartner",
  "moderatedAbroad",
  "technicalChecked",
  "cityLocative",
  "markNameEng",
  "modelNameEng",
  "regionNameEng",
  "eng",
  "hex",
  "all",
  "count",
  "seoLinkF",
  "seoLinkM",
  "seoLinkB",
  "seoLinkSX",
  "linkToCatalog",
  "status",
  "data",
  "withInfoBar",
  "infoBarText",
  "version",
  "onModeration",
  "fromArchive",
  "statusId",
  "subCategoryNameEng",
]);

const SECTION_TITLES: Record<string, string> = {
  autoData: "Автомобіль",
  stateData: "Локація",
  dealer: "Дилер",
  checkedVin: "VIN-код",
  levelData: "Розміщення",
  color: "Колір",
  technicalCondition: "Технічний стан",
  oldTop: "Топ-розміщення",
};

const FIELD_LABELS: Record<string, string> = {
  title: "Назва",
  markName: "Марка",
  modelName: "Модель",
  locationCityName: "Місто",
  USD: "Ціна в доларах",
  UAH: "Ціна в гривнях",
  EUR: "Ціна в євро",
  VIN: "VIN",
  plateNumber: "Держномер",
  addDate: "Додано",
  updateDate: "Оновлено",
  expireDate: "Діє до",
  soldDate: "Продано",
  auctionPossible: "Можливий торг",
  exchangePossible: "Можливий обмін",
  realtyExchange: "Обмін на нерухомість",
  exchangeType: "Тип обміну",
  isLeasing: "Лізинг",
  year: "Рік",
  race: "Пробіг",
  raceInt: "Пробіг (тис. км)",
  fuelName: "Паливо",
  gearboxName: "КПП",
  driveName: "Привід",
  generationName: "Покоління",
  modificationName: "Модифікація",
  equipmentName: "Комплектація",
  isSold: "Продано",
  mainCurrency: "Основна валюта",
  custom: "Розмитнення",
  withVideo: "Є відео",
  description: "Опис",
  name: "Назва",
  regionName: "Область",
  level: "Рівень топа",
  label: "Мітка",
  hotType: "Гаряче",
  isShow: "VIN опубліковано",
  linkToReport: "Звіт VIN",
  hasRestrictions: "Обмеження",
  checkDate: "Дата перевірки",
  isChecked: "Перевірено",
  vin: "VIN",
  type: "Тип",
  logo: "Логотип",
  annotation: "Примітка",
  minMonthLeasingBuPay: "Мін. платіж лізингу на місяць",
  minMonthLeasingPay: "Мін. платіж лізингу на місяць",
  isActive: "Активно",
  subCategoryName: "Тип кузова",
  technicalCondition: "Технічний стан",
};

const BODY_TYPE_LABELS: Record<string, string> = {
  khetchbek: "Хетчбек",
  hatchback: "Хетчбек",
  sedan: "Седан",
  universal: "Універсал",
  wagon: "Універсал",
  suv: "Позашляховик",
  crossover: "Кросовер",
  minivan: "Мінівен",
  pickup: "Пікап",
  cabriolet: "Кабріолет",
  cabrio: "Кабріолет",
  coupe: "Купе",
  van: "Фургон",
  liftback: "Ліфтбек",
  microbus: "Мікроавтобус",
  roadster: "Родстер",
  targa: "Тarga",
  limuzin: "Лімузин",
  limousine: "Лімузин",
};

const TOP_LEVEL_ORDER = [
  "title",
  "markName",
  "modelName",
  "subCategoryName",
  "VIN",
  "plateNumber",
  "UAH",
  "USD",
  "EUR",
  "locationCityName",
  "addDate",
  "updateDate",
  "expireDate",
  "soldDate",
  "auctionPossible",
  "exchangePossible",
  "realtyExchange",
  "exchangeType",
  "isLeasing",
];

const PRICE_FIELD_ORDER = ["UAH", "USD", "EUR", "minMonthLeasingBuPay", "minMonthLeasingPay"] as const;

function labelFor(key: string): string {
  return FIELD_LABELS[key] ?? key;
}

function isHiddenField(key: string): boolean {
  if (HIDDEN_FIELDS.has(key)) return true;
  if (key === "id" || key.endsWith("Id")) return true;
  if (key.startsWith("seoLink")) return true;
  return false;
}

function decodeBodyType(value: string): string {
  const key = value.trim().toLowerCase();
  return BODY_TYPE_LABELS[key] ?? value;
}

function decodeFieldValue(key: string, value: unknown): string | null {
  const raw = formatPrimitive(value);
  if (!raw) return null;

  if (key === "subCategoryNameEng" || key === "subCategoryName") {
    return decodeBodyType(raw);
  }

  if (key === "exchangeType" && raw === "Будь-який") {
    return "Будь-який";
  }

  return raw;
}

function formatPrimitive(value: unknown): string | null {
  if (value === null || value === undefined || value === "") return null;
  if (typeof value === "boolean") return value ? "Так" : "Ні";
  if (typeof value === "number") return String(value);
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    if (trimmed.startsWith("<svg") || trimmed.includes("xmlns=\"http://www.w3.org/2000/svg\"")) {
      return null;
    }
    return trimmed;
  }
  return null;
}

function formatPriceFieldValue(key: string, value: unknown): string | null {
  const raw = formatPrimitive(value);
  if (!raw) return null;

  if (key === "UAH") return `${raw} грн`;
  if (key === "USD") return `${raw} $`;
  if (key === "EUR") return `${raw} €`;
  if (key === "minMonthLeasingBuPay" || key === "minMonthLeasingPay") {
    return `від ${raw} грн/міс.`;
  }
  return raw;
}

function rowsFromPricesArray(prices: unknown): AutoRiaDetailRow[] {
  if (!Array.isArray(prices) || prices.length === 0) return [];

  const rows: AutoRiaDetailRow[] = [];

  prices.forEach((entry, index) => {
    if (!entry || typeof entry !== "object" || Array.isArray(entry)) return;
    const obj = entry as Record<string, unknown>;
    const prefix = prices.length > 1 ? ` (${index + 1})` : "";
    const keys = [
      ...PRICE_FIELD_ORDER,
      ...Object.keys(obj).filter(key => !PRICE_FIELD_ORDER.includes(key as (typeof PRICE_FIELD_ORDER)[number])),
    ];

    for (const key of keys) {
      if (isHiddenField(key)) continue;
      const value = obj[key];
      if (value === null || value === undefined || value === "") continue;
      const formatted = formatPriceFieldValue(key, value);
      if (!formatted) continue;
      rows.push({ label: `${labelFor(key)}${prefix}`, value: formatted });
    }
  });

  return rows;
}

function rowsFromObject(obj: Record<string, unknown>, order: string[] = []): AutoRiaDetailRow[] {
  const rows: AutoRiaDetailRow[] = [];
  const keys = [...order, ...Object.keys(obj).filter(key => !order.includes(key))];

  for (const key of keys) {
    if (isHiddenField(key)) continue;
    const value = obj[key];
    if (value === null || value === undefined || value === "") continue;

    if (Array.isArray(value) || typeof value === "object") continue;

    const formatted = decodeFieldValue(key, value);
    if (formatted) rows.push({ label: labelFor(key), value: formatted });
  }

  return rows;
}

function buildColorSection(color: Record<string, unknown>): AutoRiaDetailSection | null {
  const name = formatPrimitive(color.name);
  const hexRaw = formatPrimitive(color.hex);
  if (!name && !hexRaw) return null;

  const hex = hexRaw?.startsWith("#") ? hexRaw : hexRaw ? `#${hexRaw}` : undefined;

  return {
    title: "Колір",
    rows: [
      {
        label: "Колір",
        value: name ?? "—",
        kind: "color",
        colorHex: hex,
      },
    ],
  };
}

function buildLinkRow(sourceData: Record<string, unknown>, fallbackUrl?: string): AutoRiaDetailRow | null {
  const href =
    (typeof sourceData.linkToView === "string" && sourceData.linkToView) ||
    fallbackUrl ||
    null;

  if (!href) return null;

  return {
    label: "Оголошення",
    value: "Відкрити на AUTO.RIA",
    kind: "link",
    href,
  };
}

export function buildAutoRiaDetailSections(
  sourceData: Record<string, unknown>,
  fallbackUrl?: string,
): AutoRiaDetailSection[] {
  const enriched: Record<string, unknown> = { ...sourceData };

  if (!enriched.subCategoryName && enriched.subCategoryNameEng) {
    enriched.subCategoryName = decodeBodyType(String(enriched.subCategoryNameEng));
  }

  const sections: AutoRiaDetailSection[] = [];

  const priceRows = rowsFromPricesArray(enriched.prices);
  if (priceRows.length) {
    sections.push({ title: "Ціни", rows: priceRows });
  }

  const linkRow = buildLinkRow(enriched, fallbackUrl);
  if (linkRow) {
    sections.push({ title: "Посилання", rows: [linkRow] });
  }

  const generalRows = rowsFromObject(enriched, TOP_LEVEL_ORDER);
  if (generalRows.length) {
    sections.push({ title: "Загальне", rows: generalRows });
  }

  for (const [key, title] of Object.entries(SECTION_TITLES)) {
    if (HIDDEN_SECTIONS.has(key)) continue;

    const block = enriched[key];
    if (!block || typeof block !== "object" || Array.isArray(block)) continue;

    if (key === "color") {
      const colorSection = buildColorSection(block as Record<string, unknown>);
      if (colorSection) sections.push(colorSection);
      continue;
    }

    const rows = rowsFromObject(block as Record<string, unknown>);
    if (rows.length) sections.push({ title, rows });
  }

  const known = new Set([
    "prices",
    ...Object.keys(SECTION_TITLES),
    ...HIDDEN_SECTIONS,
    ...TOP_LEVEL_ORDER,
  ]);

  const extraRows: AutoRiaDetailRow[] = [];

  for (const [key, value] of Object.entries(enriched)) {
    if (known.has(key) || isHiddenField(key)) continue;
    if (value === null || value === undefined || value === "") continue;
    if (typeof value === "object") continue;

    const formatted = decodeFieldValue(key, value);
    if (formatted) extraRows.push({ label: labelFor(key), value: formatted });
  }

  if (extraRows.length) {
    sections.push({ title: "Додатково", rows: extraRows });
  }

  return sections;
}

export function getAutoRiaHighlights(sourceData: Record<string, unknown> | null | undefined): string[] {
  if (!sourceData) return [];
  const auto = (sourceData.autoData ?? {}) as Record<string, unknown>;
  const color = (sourceData.color ?? {}) as Record<string, unknown>;

  const bodyType =
    formatPrimitive(sourceData.subCategoryName) ||
    (sourceData.subCategoryNameEng ? decodeBodyType(String(sourceData.subCategoryNameEng)) : null);

  const items = [
    bodyType,
    auto.driveName,
    auto.generationName,
    auto.modificationName,
    auto.equipmentName,
    color.name,
    sourceData.exchangeType,
    (sourceData.levelData as Record<string, unknown> | undefined)?.hotType,
  ];

  return items
    .map(item => (typeof item === "string" ? item.trim() : item))
    .filter((item): item is string => Boolean(item));
}
