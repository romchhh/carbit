/** Курси як у backend/app/services/currency.py */
export const USD_TO_UAH = 45;
export const EUR_TO_UAH = 44;

export type DisplayCurrency = "UAH" | "USD" | "EUR";

export const DISPLAY_CURRENCY_OPTIONS: {
  value: DisplayCurrency;
  label: string;
  suffix: string;
}[] = [
  { value: "UAH", label: "Гривня", suffix: "грн" },
  { value: "USD", label: "Долар", suffix: "$" },
  { value: "EUR", label: "Євро", suffix: "€" },
];

export function resolveDisplayCurrency(value: string | null | undefined): DisplayCurrency {
  const cur = (value || "UAH").toUpperCase();
  if (cur === "USD" || cur === "EUR" || cur === "UAH") return cur;
  if (cur === "ГРН" || cur === "UA") return "UAH";
  if (cur === "$" || cur === "US") return "USD";
  if (cur === "€" || cur === "EU" || cur === "EURO") return "EUR";
  return "UAH";
}

export function currencySuffix(currency: DisplayCurrency): string {
  if (currency === "USD") return "$";
  if (currency === "EUR") return "€";
  return "грн";
}

/** Ціни в API зберігаються в грн. */
export function fromUah(amountUah: number, target: DisplayCurrency): number {
  const value = Number(amountUah) || 0;
  if (target === "USD") return Math.round(value / USD_TO_UAH);
  if (target === "EUR") return Math.round(value / EUR_TO_UAH);
  return Math.round(value);
}

export function formatPriceFromUah(
  amountUah: number,
  target: DisplayCurrency | string | null | undefined = "UAH",
): string {
  const currency = resolveDisplayCurrency(target);
  const amount = fromUah(amountUah, currency);
  const formatted = new Intl.NumberFormat("uk-UA").format(amount);
  const suffix = currencySuffix(currency);
  return `${formatted} ${suffix}`;
}
