/**
 * Орієнтовний кредит «готівка на автівку» — kalkulyator_gotivka-na-avtivku.xlsx
 *
 * Сценарії:
 * - with_registration: «Графік платежів 1» — фікс. 29,95% (D9), PPMT/IPMT
 * - without_registration: «Графік платежів 2» — 1-й період 29,95%, далі 55,95% (H7) на залишок F25
 *
 * Комісії: C11 2,95%; C10 0%; P12 0,12%×сума×строк (опц.); UIDR+маржа з 25-го місяця (опц.)
 */

import {
  nativeAmountFromSourceData,
  resolveListingCurrency,
  toUah,
} from "@/lib/display-currency";
import type { Listing } from "@/types/api";

export const BISBANK_LOAN_MIN_UAH = 5_000;
export const BISBANK_LOAN_MAX_UAH = 500_000;
export const BISBANK_TERM_MIN_MONTHS = 6;
export const BISBANK_TERM_MAX_MONTHS = 60;

export const BISBANK_RATE_NOMINAL = 0.29949999999999999;
export const BISBANK_RATE_WITHOUT_REG_FROM_MONTH2 = 0.5595;
export const BISBANK_ONE_TIME_FEE_RATE = 0.0295;
export const BISBANK_MONTHLY_FEE_RATE = 0;
/** F14 — ставка з 25-го місяця при UIDR (якщо індекс > 0). */
export const BISBANK_FLOATING_MARGIN_DEFAULT = 0.1699;
export const BISBANK_NOTARY_RATE_PER_TERM = 0.0012;

export const BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT = 15;
export const BISBANK_DEFAULT_TERM_MONTHS = 36;

export type BisbankRegistrationMode = "with_registration" | "without_registration";

export type BisbankCreditOptions = {
  /** M12 «наявне» — нотаріальні/держмито P12. */
  includeNotaryFee?: boolean;
  /** F12+F13 > 0 — з 25-го місяця ставка = uidrIndex + margin (інакше номінал на весь строк). */
  uidrIndex?: number;
  margin?: number;
};

export type BisbankCreditInputs = {
  carPriceUah: number;
  downPaymentPercent: number;
  termMonths: number;
  registrationMode?: BisbankRegistrationMode;
  options?: BisbankCreditOptions;
  /** Як D3 у файлі банку; за замовчуванням — сьогодні. */
  creditDate?: Date;
};

export type BisbankPaymentScheduleRow = {
  /** 0 — видача кредиту, 1…n — платіж. */
  index: number;
  paymentDate: Date;
  daysInPeriod: number | null;
  balanceBeforeUah: number;
  principalUah: number;
  interestUah: number;
  monthlyFeeUah: number;
  oneTimeFeeUah: number;
  notaryUah: number;
  /** Сума платежу за період (як кол. H, без знаку). */
  paymentTotalUah: number;
  /** Грошовий потік позичальника для XIRR (як кол. H: видача +, платежі −). */
  cashflowUah: number;
  balanceAfterUah: number;
  annualRate: number;
};

export type BisbankCreditQuote = {
  carPriceUah: number;
  downPaymentUah: number;
  downPaymentPercent: number;
  loanAmountUah: number;
  termMonths: number;
  registrationMode: BisbankRegistrationMode;
  creditDate: Date;
  maturityDate: Date | null;
  netDisbursementUah: number;
  nominalRatePercent: number;
  secondaryRatePercent: number | null;
  monthlyPaymentUah: number;
  monthlyPaymentFromMonth2Uah: number | null;
  oneTimeFeeUah: number;
  notaryFeeUah: number;
  totalInterestUah: number;
  totalRepaymentUah: number;
  totalConsumerCostUah: number;
  realAnnualRatePercent: number | null;
  paymentSchedule: BisbankPaymentScheduleRow[];
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

export function minDownPaymentPercent(carPriceUah: number): number {
  const price = Math.max(0, Math.round(carPriceUah));
  if (price <= BISBANK_LOAN_MAX_UAH) return 0;
  const minDown = price - BISBANK_LOAN_MAX_UAH;
  return Math.ceil((minDown / price) * 1000) / 10;
}

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value));
}

/** Excel PMT (платіж додатний). */
export function pmtPositive(annualRate: number, termMonths: number, loanAmount: number): number {
  const n = Math.max(1, Math.round(termMonths));
  const pv = Math.max(0, loanAmount);
  if (pv === 0) return 0;
  const r = annualRate / 12;
  if (Math.abs(r) < 1e-12) return pv / n;
  const factor = (1 + r) ** n;
  return (pv * r * factor) / (factor - 1);
}

/** Excel PPMT — погашення тіла (додатне). */
function ppmtPositive(
  annualRate: number,
  period: number,
  termMonths: number,
  loanAmount: number,
): number {
  const n = Math.max(1, Math.round(termMonths));
  const per = clamp(Math.round(period), 1, n);
  const r = annualRate / 12;
  const payment = pmtPositive(annualRate, n, loanAmount);
  let balance = loanAmount;
  for (let i = 1; i < per; i++) {
    const interest = balance * r;
    const principal = payment - interest;
    balance -= principal;
  }
  const interest = balance * r;
  return payment - interest;
}

function ipmtPositive(
  annualRate: number,
  period: number,
  termMonths: number,
  loanAmount: number,
): number {
  const n = Math.max(1, Math.round(termMonths));
  const per = clamp(Math.round(period), 1, n);
  const r = annualRate / 12;
  let balance = loanAmount;
  for (let i = 1; i < per; i++) {
    const payment = pmtPositive(annualRate, n, loanAmount);
    balance -= payment - balance * r;
  }
  return balance * r;
}

function startOfLocalDay(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}

/** Дата платежу: 10-те число місяця EDATE(дата кредиту, n). */
export function bisbankPaymentDate(creditDate: Date, paymentIndex: number): Date {
  const base = startOfLocalDay(creditDate);
  const d = new Date(base.getFullYear(), base.getMonth() + paymentIndex, 10);
  return d;
}

export function bisbankMaturityDate(creditDate: Date, termMonths: number): Date {
  return bisbankPaymentDate(creditDate, termMonths);
}

function daysBetween(from: Date, to: Date): number {
  const ms = startOfLocalDay(to).getTime() - startOfLocalDay(from).getTime();
  return Math.round(ms / 86_400_000);
}

export function buildBisbankPaymentSchedule(params: {
  loanAmountUah: number;
  termMonths: number;
  registrationMode: BisbankRegistrationMode;
  uidrIndex: number;
  margin: number;
  oneTimeFeeUah: number;
  notaryFeeUah: number;
  creditDate: Date;
}): BisbankPaymentScheduleRow[] {
  const n = Math.max(1, Math.round(params.termMonths));
  const loan = Math.max(0, params.loanAmountUah);
  const creditDate = startOfLocalDay(params.creditDate);
  const rows: BisbankPaymentScheduleRow[] = [];

  const disbursementDate = creditDate;
  const netLoan = loan - params.oneTimeFeeUah - params.notaryFeeUah;
  rows.push({
    index: 0,
    paymentDate: disbursementDate,
    daysInPeriod: null,
    balanceBeforeUah: loan,
    principalUah: 0,
    interestUah: 0,
    monthlyFeeUah: 0,
    oneTimeFeeUah: params.oneTimeFeeUah,
    notaryUah: params.notaryFeeUah,
    paymentTotalUah: 0,
    cashflowUah: netLoan,
    balanceAfterUah: loan,
    annualRate: BISBANK_RATE_NOMINAL,
  });

  if (loan === 0) return rows;

  const floatingStartsAt = 25;
  const useFloating =
    params.registrationMode === "with_registration" &&
    params.uidrIndex + params.margin > 1e-9 &&
    n >= floatingStartsAt;

  let balance = loan;
  let prevDate = disbursementDate;
  let withoutRegPhase2Pv = 0;
  let withoutRegPhase2N = 0;
  let withoutRegSteadyPayment = 0;

  for (let month = 1; month <= n; month++) {
    const paymentDate = bisbankPaymentDate(creditDate, month);
    const daysInPeriod = daysBetween(prevDate, paymentDate);
    prevDate = paymentDate;

    let annualRate = BISBANK_RATE_NOMINAL;
    let payment = 0;
    let principal = 0;
    let interest = 0;

    if (params.registrationMode === "without_registration") {
      if (month === 1) {
        annualRate = BISBANK_RATE_NOMINAL;
        payment = pmtPositive(annualRate, n, loan);
        principal = ppmtPositive(annualRate, 1, n, loan);
        interest = ipmtPositive(annualRate, 1, n, loan);
        withoutRegPhase2Pv = loan - principal;
        withoutRegPhase2N = n - 1;
        withoutRegSteadyPayment =
          withoutRegPhase2N > 0
            ? pmtPositive(BISBANK_RATE_WITHOUT_REG_FROM_MONTH2, withoutRegPhase2N, withoutRegPhase2Pv)
            : 0;
      } else {
        annualRate = BISBANK_RATE_WITHOUT_REG_FROM_MONTH2;
        payment = withoutRegSteadyPayment;
        principal = ppmtPositive(
          annualRate,
          month - 1,
          withoutRegPhase2N,
          withoutRegPhase2Pv,
        );
        interest = payment - principal;
      }
    } else if (useFloating && month >= floatingStartsAt) {
      annualRate = params.uidrIndex + params.margin;
      const remaining = n - month + 1;
      payment = pmtPositive(annualRate, remaining, balance);
      interest = balance * (annualRate / 12);
      principal = payment - interest;
    } else if (useFloating) {
      annualRate = BISBANK_RATE_NOMINAL;
      payment = pmtPositive(annualRate, n, loan);
      principal = ppmtPositive(annualRate, month, n, loan);
      interest = ipmtPositive(annualRate, month, n, loan);
    } else {
      annualRate = BISBANK_RATE_NOMINAL;
      payment = pmtPositive(annualRate, n, loan);
      principal = ppmtPositive(annualRate, month, n, loan);
      interest = ipmtPositive(annualRate, month, n, loan);
    }

    const monthlyFeeUah = Math.round(loan * BISBANK_MONTHLY_FEE_RATE);
    const paymentTotal = payment + monthlyFeeUah;
    balance = Math.max(0, balance - principal);

    rows.push({
      index: month,
      paymentDate,
      daysInPeriod,
      balanceBeforeUah: balance + principal,
      principalUah: principal,
      interestUah: interest,
      monthlyFeeUah,
      oneTimeFeeUah: 0,
      notaryUah: 0,
      paymentTotalUah: paymentTotal,
      cashflowUah: -paymentTotal,
      balanceAfterUah: balance,
      annualRate,
    });
  }

  return rows;
}

function xirrFromSchedule(
  creditDate: Date,
  schedule: BisbankPaymentScheduleRow[],
): number | null {
  const origin = startOfLocalDay(creditDate);
  const flows = schedule.map(row => ({
    amount: row.cashflowUah,
    dayOffset: daysBetween(origin, row.paymentDate),
  }));
  return computeXirr(flows);
}

/** XIRR (як Excel) — денні потоки, початок t=0. */
export function computeXirr(
  cashflows: { amount: number; dayOffset: number }[],
  guess = 0.1,
): number | null {
  if (cashflows.length < 2) return null;
  const hasPos = cashflows.some(c => c.amount > 0);
  const hasNeg = cashflows.some(c => c.amount < 0);
  if (!hasPos || !hasNeg) return null;

  const npv = (rate: number) =>
    cashflows.reduce((sum, cf) => {
      const t = cf.dayOffset / 365;
      return sum + cf.amount / (1 + rate) ** t;
    }, 0);

  const dNpv = (rate: number) =>
    cashflows.reduce((sum, cf) => {
      const t = cf.dayOffset / 365;
      if (t === 0) return sum;
      return sum - (t * cf.amount) / (1 + rate) ** (t + 1);
    }, 0);

  let rate = guess;
  for (let i = 0; i < 64; i++) {
    const f = npv(rate);
    const df = dNpv(rate);
    if (!Number.isFinite(f) || !Number.isFinite(df) || Math.abs(df) < 1e-12) break;
    const next = rate - f / df;
    if (!Number.isFinite(next) || next <= -0.999) break;
    if (Math.abs(next - rate) < 1e-10) {
      rate = next;
      break;
    }
    rate = next;
  }
  if (!Number.isFinite(rate) || rate <= -0.999) return null;
  return rate;
}

export function computeBisbankCreditQuote(input: BisbankCreditInputs): BisbankCreditQuote {
  const warnings: string[] = [];
  const registrationMode = input.registrationMode ?? "with_registration";
  const options = input.options ?? {};
  const includeNotary = Boolean(options.includeNotaryFee);
  const uidrIndex = Math.max(0, options.uidrIndex ?? 0);
  const margin = Math.max(0, options.margin ?? 0);

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

  const oneTimeFeeUah = loanValid
    ? Math.round(loanAmountUah * BISBANK_ONE_TIME_FEE_RATE)
    : 0;
  const notaryFeeUah =
    loanValid && includeNotary
      ? Math.round(loanAmountUah * termMonths * BISBANK_NOTARY_RATE_PER_TERM)
      : 0;

  const creditDate = startOfLocalDay(input.creditDate ?? new Date());
  const paymentSchedule = loanValid
    ? buildBisbankPaymentSchedule({
        loanAmountUah,
        termMonths,
        registrationMode,
        uidrIndex,
        margin,
        oneTimeFeeUah,
        notaryFeeUah,
        creditDate,
      })
    : [];

  const paymentRows = paymentSchedule.filter(r => r.index > 0);
  const monthlyPaymentUah =
    paymentRows.length > 0 ? Math.round(paymentRows[0].paymentTotalUah) : 0;
  const monthlyPaymentFromMonth2Uah =
    registrationMode === "without_registration" && paymentRows.length > 1
      ? Math.round(paymentRows[1].paymentTotalUah)
      : null;

  const totalInterestUah = Math.round(
    paymentRows.reduce((s, r) => s + r.interestUah, 0),
  );
  const totalRepaymentUah = Math.round(
    paymentRows.reduce((s, r) => s + r.paymentTotalUah, 0) +
      oneTimeFeeUah +
      notaryFeeUah,
  );
  const totalConsumerCostUah = totalRepaymentUah;
  const netDisbursementUah = loanValid
    ? Math.round(loanAmountUah - oneTimeFeeUah - notaryFeeUah)
    : 0;

  let realAnnualRatePercent: number | null = null;
  if (loanValid && paymentSchedule.length > 1) {
    const xirr = xirrFromSchedule(creditDate, paymentSchedule);
    if (xirr != null) {
      realAnnualRatePercent = Math.round(xirr * 10000) / 100;
    }
  }

  const maturityDate = loanValid ? bisbankMaturityDate(creditDate, termMonths) : null;

  const nominalRatePercent = Math.round(BISBANK_RATE_NOMINAL * 10000) / 100;
  const secondaryRatePercent =
    registrationMode === "without_registration"
      ? Math.round(BISBANK_RATE_WITHOUT_REG_FROM_MONTH2 * 10000) / 100
      : null;

  if (registrationMode === "without_registration") {
    warnings.push(
      "Без підтвердження реєстрації ТЗ у банку застосовується підвищена ставка з 2-го місяця (як «Графік платежів 2»).",
    );
  }
  if (uidrIndex + margin > 0 && termMonths >= 25 && registrationMode === "with_registration") {
    warnings.push(
      `З 25-го місяця застосовується плаваюча ставка ${formatPercentUk((uidrIndex + margin) * 100, 2)} (UIDR + маржа).`,
    );
  }

  return {
    carPriceUah,
    downPaymentUah,
    downPaymentPercent,
    loanAmountUah,
    termMonths,
    registrationMode,
    creditDate,
    maturityDate,
    netDisbursementUah,
    nominalRatePercent,
    secondaryRatePercent,
    monthlyPaymentUah,
    monthlyPaymentFromMonth2Uah,
    oneTimeFeeUah,
    notaryFeeUah,
    totalInterestUah,
    totalRepaymentUah,
    totalConsumerCostUah,
    realAnnualRatePercent,
    paymentSchedule,
    loanValid,
    warnings,
  };
}

/** @deprecated використовуйте computeBisbankCreditQuote */
export function annuityMonthlyPaymentUah(
  loanAmountUah: number,
  termMonths: number,
  annualRate = BISBANK_RATE_NOMINAL,
): number {
  return pmtPositive(annualRate, termMonths, loanAmountUah);
}

export const BISBANK_ANNUAL_RATE = BISBANK_RATE_NOMINAL;

export function formatMoneyUah(value: number): string {
  return `${new Intl.NumberFormat("uk-UA").format(Math.round(value))} грн`;
}

export function formatPercentUk(value: number, digits = 1): string {
  return `${value.toFixed(digits).replace(".", ",")}%`;
}

export function formatBisbankDateUk(d: Date): string {
  return new Intl.DateTimeFormat("uk-UA", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
  }).format(d);
}

export function formatMoneyTableUah(value: number): string {
  return new Intl.NumberFormat("uk-UA", {
    maximumFractionDigits: 0,
  }).format(Math.round(value));
}

export const BISBANK_TERM_MARKS = [6, 12, 24, 36, 48, 60] as const;
