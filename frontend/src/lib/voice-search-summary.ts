export type VoiceFilterChip = {
  key: string;
  label: string;
  value: string;
};

const CURRENCY_SYMBOL: Record<string, string> = {
  USD: "$",
  UAH: "₴",
  EUR: "€",
};

function formatPrice(value: unknown, currency: string): string {
  const num = Number(value);
  if (!Number.isFinite(num)) return String(value);
  const symbol = CURRENCY_SYMBOL[currency] ?? currency;
  return `${symbol}${num.toLocaleString("uk-UA")}`;
}

function formatList(value: unknown): string {
  if (!Array.isArray(value) || !value.length) return "";
  return value.map(String).join(", ");
}

/** Чіпи розпізнаних фільтрів для превʼю в оверлеї. */
export function buildVoiceFilterChips(
  raw: Record<string, unknown> | null | undefined,
  options?: { marketDiscovery?: boolean },
): VoiceFilterChip[] {
  if (!raw || typeof raw !== "object") return [];

  const chips: VoiceFilterChip[] = [];
  const currency = String(raw.currency || "USD").toUpperCase();
  const marketDiscovery = options?.marketDiscovery ?? false;

  if (marketDiscovery && !raw.brand) {
    chips.push({ key: "market", label: "Пошук", value: "По всьому ринку" });
  }

  if (raw.brand) {
    chips.push({ key: "brand", label: "Марка", value: String(raw.brand) });
  }
  if (raw.model) {
    chips.push({ key: "model", label: "Модель", value: String(raw.model) });
  }
  if (raw.price_from != null || raw.price_to != null) {
    const from = raw.price_from != null ? formatPrice(raw.price_from, currency) : null;
    const to = raw.price_to != null ? formatPrice(raw.price_to, currency) : null;
    const value =
      from && to ? `${from} – ${to}` : to ? `до ${to}` : from ? `від ${from}` : "";
    if (value) {
      chips.push({
        key: "price",
        label: marketDiscovery && !raw.brand ? "Бюджет" : "Ціна",
        value,
      });
    }
  }
  if (raw.year_from != null || raw.year_to != null) {
    const from = raw.year_from != null ? String(raw.year_from) : null;
    const to = raw.year_to != null ? String(raw.year_to) : null;
    const value = from && to ? `${from}–${to}` : from ? `від ${from}` : to ? `до ${to}` : "";
    if (value) chips.push({ key: "year", label: "Рік", value });
  }
  if (raw.mileage_to != null) {
    chips.push({ key: "mileage", label: "Пробіг", value: `до ${raw.mileage_to} тис. км` });
  }
  if (raw.region) {
    chips.push({
      key: "region",
      label: "Регіон",
      value: String(raw.region).replace(/^м\.\s*/i, ""),
    });
  }
  const fuels = formatList(raw.fuel);
  if (fuels) chips.push({ key: "fuel", label: "Паливо", value: fuels });
  const transmissions = formatList(raw.transmission);
  if (transmissions) chips.push({ key: "transmission", label: "КПП", value: transmissions });
  const bodyTypes = formatList(raw.body_types);
  if (bodyTypes) chips.push({ key: "body", label: "Кузов", value: bodyTypes });

  return chips;
}

export const VOICE_SEARCH_EXAMPLES = [
  "У мене є 15 тис. $ — знайди авто 2020–2022",
  "Toyota Camry до 18 тис. $, від 2018",
  "BMW X5 дизель, автомат, Львів",
] as const;

export function isMarketDiscoveryResult(result: {
  search_intent?: string | null;
  filters?: Record<string, unknown>;
}): boolean {
  return result.search_intent === "market_discovery";
}
