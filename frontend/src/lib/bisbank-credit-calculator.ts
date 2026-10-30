/**
 * Орієнтовний кредит «готівка на автівку» — формули з kalkulyator_gotivka-na-avtivku.xlsx
 * (лист «Графік платежів 1» / « », цільове використання — з реєстрацією ТЗ).
 *
 * - C7/C8/C9/C11: сума, строк, ставка, разова комісія
 * - G9: -PMT(D9/12, D8, D6)
 * - N4: N3 * D6 (разова комісія 2,95%)
 */

import {
  nativeAmountFromSourceData,
  resolveListingCurrency,
  toUah,
} from "@/lib/display-currency";
import type { Listing } from "@/types/api";

/** Мін. / макс. сума кредиту (грн) — D7 на «Графік платежів 1». */
export const BISBANK_LOAN_MIN_UAH = 5_000;
export const BISBANK_LOAN_MAX_UAH = 500_000;

export const BISBANK_TERM_MIN_MONTHS = 6;
export const BISBANK_TERM_MAX_MONTHS = 60;

/** C9 — фіксована річна ставка, % у частках. */
export const BISBANK_ANNUAL_RATE = 0.29949999999999999;

/** C11 — разова комісія за надання кредиту. */
export const BISBANK_ONE_TIME_FEE_RATE = 0.0295;

/** C10 — щомісячна комісія (% від суми кредиту). */
export const BISBANK_MONTHLY_FEE_RATE = 0;

export const BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT = 15;
export const BISBANK_DEFAULT_TERM_MONTHS = 36;

export type BisbankCreditInputs = {
  carPriceUah: number;
  downPaymentPercent: number;
  termMonths: number;
};

export type BisbankCreditQuote = {
  carPriceUah: number;
  downPaymentUah: number;
  downPaymentPercent: number;
  loanAmountUah: number;
  termMonths: number;
  annualRatePercent: number;
  monthlyPaymentUah: number;
  oneTimeFeeUah: number;
  totalRepaymentUah: number;
  loanValid: boolean;
  warnings: string[];
};

export function resolveListingPriceUah(listing: Listing): number {
  const from = resolveListingCurrency(listing.currency);
  const nativeFrom = nativeAmountFromSourceData(listing.source_data, from);
  const raw =
    nativeFrom != null && nativeFrom > 0 ? nativeFrom : Number(listing.price) || 0;
  return toUah(raw, from);
}

/** Мін. % першого внеску, щоб сума кредиту не перевищувала ліміт банку. */
export function minDownPaymentPercent(carPriceUah: number): number {
  const price = Math.max(0, Math.round(carPriceUah));
  if (price <= BISBANK_LOAN_MAX_UAH) return 0;
  const minDown = price - BISBANK_LOAN_MAX_UAH;
  return Math.ceil((minDown / price) * 1000) / 10;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Excel PMT — щомісячний ануїтетний платіж (повні періоди). */
export function annuityMonthlyPaymentUah(
  loanAmountUah: number,
  termMonths: number,
  annualRate = BISBANK_ANNUAL_RATE,
): number {
  const principal = Math.max(0, loanAmountUah);
  const n = Math.max(1, Math.round(termMonths));
  if (principal === 0) return 0;
  const r = annualRate / 12;
  if (r === 0) return principal / n;
  const factor = (1 + r) ** n;
  return (principal * r * factor) / (factor - 1);
}

export function computeBisbankCreditQuote(input: BisbankCreditInputs): BisbankCreditQuote {
  const warnings: string[] = [];
  const carPriceUah = Math.max(0, Math.round(input.carPriceUah));
  const termMonths = clamp(
    Math.round(input.termMonths),
    BISBANK_TERM_MIN_MONTHS,
    BISBANK_TERM_MAX_MONTHS,
  );

  const minDown = minDownPaymentPercent(carPriceUah);
  let downPaymentPercent = clamp(input.downPaymentPercent, minDown, 95);

  if (input.downPaymentPercent < minDown) {
    warnings.push(
      `Для цього авто мінімальний перший внесок — ${formatPercentUk(minDown)} (ліміт кредиту ${formatMoneyUah(BISBANK_LOAN_MAX_UAH)}).`,
    );
  }

  let downPaymentUah = Math.round((carPriceUah * downPaymentPercent) / 100);
  let loanAmountUah = Math.max(0, carPriceUah - downPaymentUah);

  if (loanAmountUah > BISBANK_LOAN_MAX_UAH) {
    loanAmountUah = BISBANK_LOAN_MAX_UAH;
    downPaymentUah = Math.max(0, carPriceUah - loanAmountUah);
    downPaymentPercent =
      carPriceUah > 0 ? Math.round((downPaymentUah / carPriceUah) * 1000) / 10 : 0;
  }

  const loanValid =
    carPriceUah > 0 &&
    loanAmountUah >= BISBANK_LOAN_MIN_UAH &&
    loanAmountUah <= BISBANK_LOAN_MAX_UAH;

  if (carPriceUah > 0 && loanAmountUah < BISBANK_LOAN_MIN_UAH) {
    warnings.push(`Мін. сума кредиту — ${formatMoneyUah(BISBANK_LOAN_MIN_UAH)}.`);
  }
  if (loanAmountUah > BISBANK_LOAN_MAX_UAH) {
    warnings.push(`Максимальна сума кредиту — ${formatMoneyUah(BISBANK_LOAN_MAX_UAH)}.`);
  }

  const monthlyRaw = loanValid
    ? annuityMonthlyPaymentUah(loanAmountUah, termMonths)
    : 0;
  const monthlyPaymentUah = Math.round(monthlyRaw);

  const oneTimeFeeUah = loanValid
    ? Math.round(loanAmountUah * BISBANK_ONE_TIME_FEE_RATE)
    : 0;
  const monthlyFeeUah = loanValid
    ? Math.round(loanAmountUah * BISBANK_MONTHLY_FEE_RATE * termMonths)
    : 0;
  const totalRepaymentUah = monthlyPaymentUah * termMonths + oneTimeFeeUah + monthlyFeeUah;

  return {
    carPriceUah,
    downPaymentUah,
    downPaymentPercent,
    loanAmountUah,
    termMonths,
    annualRatePercent: Math.round(BISBANK_ANNUAL_RATE * 10000) / 100,
    monthlyPaymentUah,
    oneTimeFeeUah,
    totalRepaymentUah,
    loanValid,
    warnings,
  };
}

export function formatMoneyUah(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(Math.round(value))} грн`;
}

export function formatPercentUk(value: number, digits = 1): string {
  return `${value.toFixed(digits).replace(".", ",")}%`;
}

export const BISBANK_TERM_MARKS = [6, 12, 24, 36, 48, 60] as const;
