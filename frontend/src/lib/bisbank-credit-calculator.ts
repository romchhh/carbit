/**
 * Орієнтовний кредит «готівка на автівку» — лист «Графік платежів».
 *
 * Один сценарій: фіксована 29,95% (C9) на весь строк, ануїтет PPMT/IPMT.
 * Разова комісія C11 2,95%, щомісячна C10 0%.
 * Нотаріальні 0,12% і плаваюча ставка UIDR з 25-го місяця не застосовуються.
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

export const BISBANK_RATE_NOMINAL = 0.2995;
export const BISBANK_ONE_TIME_FEE_RATE = 0.0295;
export const BISBANK_MONTHLY_FEE_RATE = 0;

export const BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT = 15;
export const BISBANK_DEFAULT_TERM_MONTHS = 36;

export type BisbankRegistrationMode = "with_registration";

export type BisbankCreditInputs = {
  carPriceUah: number;
  downPaymentPercent: number;
  termMonths: number;
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
  oneTimeFeeUah: number;
  creditDate: Date;
}): BisbankPaymentScheduleRow[] {
  const n = Math.max(1, Math.round(params.termMonths));
  const loan = Math.max(0, params.loanAmountUah);
  const creditDate = startOfLocalDay(params.creditDate);
  const rows: BisbankPaymentScheduleRow[] = [];

  const disbursementDate = creditDate;
  const netLoan = loan - params.oneTimeFeeUah;
  rows.push({
    index: 0,
    paymentDate: disbursementDate,
    daysInPeriod: null,
    balanceBeforeUah: loan,
    principalUah: 0,
    interestUah: 0,
    monthlyFeeUah: 0,
    oneTimeFeeUah: params.oneTimeFeeUah,
    notaryUah: 0,
    paymentTotalUah: 0,
    cashflowUah: netLoan,
    balanceAfterUah: loan,
    annualRate: BISBANK_RATE_NOMINAL,
  });

  if (loan === 0) return rows;

  let balance = loan;
  let prevDate = disbursementDate;
  const annualRate = BISBANK_RATE_NOMINAL;

  for (let month = 1; month <= n; month++) {
    const paymentDate = bisbankPaymentDate(creditDate, month);
    const daysInPeriod = daysBetween(prevDate, paymentDate);
    prevDate = paymentDate;

    const payment = pmtPositive(annualRate, n, loan);
    const principal = ppmtPositive(annualRate, month, n, loan);
    const interest = ipmtPositive(annualRate, month, n, loan);
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
  const registrationMode: BisbankRegistrationMode = "with_registration";

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
  const notaryFeeUah = 0;

  const creditDate = startOfLocalDay(input.creditDate ?? new Date());
  const paymentSchedule = loanValid
    ? buildBisbankPaymentSchedule({
        loanAmountUah,
        termMonths,
        oneTimeFeeUah,
        creditDate,
      })
    : [];

  const paymentRows = paymentSchedule.filter(r => r.index > 0);
  const monthlyPaymentUah =
    paymentRows.length > 0 ? Math.round(paymentRows[0].paymentTotalUah) : 0;
  const monthlyPaymentFromMonth2Uah = null;

  const totalInterestUah = Math.round(
    paymentRows.reduce((s, r) => s + r.interestUah, 0),
  );
  const totalRepaymentUah = Math.round(
    paymentRows.reduce((s, r) => s + r.paymentTotalUah, 0) + oneTimeFeeUah,
  );
  const totalConsumerCostUah = totalRepaymentUah;
  const netDisbursementUah = loanValid
    ? Math.round(loanAmountUah - oneTimeFeeUah)
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
  const secondaryRatePercent = null;

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
