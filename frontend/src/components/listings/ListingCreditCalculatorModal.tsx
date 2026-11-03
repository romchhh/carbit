"use client";

import Image from "next/image";
import Link from "next/link";
import { useDeferredValue, useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { PhoneInput, normalizePhoneForApi } from "@/components/auth/PhoneInput";
import { IconInfo, IconX } from "@/components/icons";
import { ListingPhoto } from "@/components/listings/ListingPhoto";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/contexts/AuthProvider";
import { BANK_PARTNER_BIZBANK } from "@/lib/brand-assets";
import { BisbankPaymentScheduleTable } from "@/components/listings/BisbankPaymentScheduleTable";
import {
  BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT,
  BISBANK_DEFAULT_TERM_MONTHS,
  BISBANK_FLOATING_MARGIN_DEFAULT,
  BISBANK_TERM_MARKS,
  BISBANK_TERM_MAX_MONTHS,
  BISBANK_TERM_MIN_MONTHS,
  computeBisbankCreditQuote,
  formatBisbankDateUk,
  formatMoneyUah,
  formatPercentUk,
  minDownPaymentPercent,
  resolveListingPriceUah,
  type BisbankRegistrationMode,
} from "@/lib/bisbank-credit-calculator";
import { cn } from "@/lib/utils";
import { ApiError, creditLeads } from "@/lib/api";
import { formatListingPrice, type DisplayCurrency } from "@/lib/display-currency";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import type { Listing } from "@/types/api";

type Props = {
  open: boolean;
  listing: Listing;
  displayCurrency: DisplayCurrency;
  onClose: () => void;
};

const CREDIT_CALC_DISCLAIMER =
  "Розрахунок орієнтовний, за методикою калькулятора БІЗБАНК («готівка на автівку»): ануїтет, разова комісія 2,95%, сценарії з реєстрацією та без. Реальна річна ставка (XIRR) враховує комісії та графік платежів і може відрізнятися від номінальної. Надсилання заявки не є публічною офертою; рішення приймає банк.";

function phoneNationalFromStored(phone: string | null | undefined): string {
  if (!phone) return "";
  const digits = phone.replace(/\D/g, "");
  let national = digits;
  if (national.startsWith("380")) national = national.slice(3);
  else if (national.startsWith("80")) national = national.slice(2);
  else if (national.startsWith("0")) national = national.slice(1);
  national = national.slice(0, 9);
  if (national.length < 9) return "";
  return `${national.slice(0, 2)} ${national.slice(2, 5)} ${national.slice(5, 7)} ${national.slice(7, 9)}`;
}

function CreditSlider({
  id,
  label,
  valueLabel,
  min,
  max,
  step,
  value,
  onChange,
  marks,
  formatMark,
}: {
  id: string;
  label: string;
  valueLabel: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (next: number) => void;
  marks?: readonly number[];
  formatMark?: (mark: number, max: number) => string;
}) {
  return (
    <div className="rounded-xl bg-surface/50 px-3 py-3">
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-[13px] font-medium text-ink">
          {label}
        </label>
        <span className="shrink-0 whitespace-nowrap text-[14px] font-semibold tabular-nums tracking-tight text-ink">
          {valueLabel}
        </span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="credit-slider mt-3 w-full"
      />
      {marks && marks.length > 0 ? (
        <div className="mt-2 flex justify-between text-[11px] tabular-nums text-ink/75">
          {marks.map(mark => (
            <span key={mark}>
              {formatMark ? formatMark(mark, max) : String(mark)}
            </span>
          ))}
        </div>
      ) : null}
    </div>
  );
}

export function ListingCreditCalculatorModal({
  open,
  listing,
  displayCurrency,
  onClose,
}: Props) {
  const { user } = useAuth();
  const carPriceUah = resolveListingPriceUah(listing);
  const minDown = minDownPaymentPercent(carPriceUah);
  const downMin = Math.max(10, Math.ceil(minDown));

  const [downPercent, setDownPercent] = useState(() =>
    Math.max(BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT, downMin),
  );
  const [termMonths, setTermMonths] = useState(BISBANK_DEFAULT_TERM_MONTHS);
  const [registrationMode, setRegistrationMode] =
    useState<BisbankRegistrationMode>("with_registration");
  const [includeNotary, setIncludeNotary] = useState(false);
  const [uidrIndexPercent, setUidrIndexPercent] = useState("");
  const [marginPercent, setMarginPercent] = useState("");
  const [applicationOpen, setApplicationOpen] = useState(false);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [submitOk, setSubmitOk] = useState(false);
  const [quoteDetailsOpen, setQuoteDetailsOpen] = useState(false);
  const [disclaimerOpen, setDisclaimerOpen] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDownPercent(prev => Math.max(prev, downMin, BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT));
    setTermMonths(BISBANK_DEFAULT_TERM_MONTHS);
    setRegistrationMode("with_registration");
    setIncludeNotary(false);
    setUidrIndexPercent("");
    setMarginPercent("");
    setApplicationOpen(false);
    setQuoteDetailsOpen(false);
    setDisclaimerOpen(false);
    setSubmitError("");
    setSubmitOk(false);
    setName(user?.name?.trim() ?? "");
    setPhone(phoneNationalFromStored(user?.phone));
  }, [open, listing.id, downMin, user?.name, user?.phone]);

  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (disclaimerOpen) {
        setDisclaimerOpen(false);
        return;
      }
      onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose, disclaimerOpen]);

  const deferredDownPercent = useDeferredValue(downPercent);
  const deferredTermMonths = useDeferredValue(termMonths);
  const quote = useMemo(() => {
    const uidr = parseFloat(uidrIndexPercent.replace(",", "."));
    const margin = parseFloat(marginPercent.replace(",", "."));
    return computeBisbankCreditQuote({
      carPriceUah,
      downPaymentPercent: deferredDownPercent,
      termMonths: deferredTermMonths,
      registrationMode,
      options: {
        includeNotaryFee: includeNotary,
        uidrIndex: Number.isFinite(uidr) ? uidr / 100 : 0,
        margin: Number.isFinite(margin) ? margin / 100 : 0,
      },
    });
  }, [
    carPriceUah,
    deferredDownPercent,
    deferredTermMonths,
    registrationMode,
    includeNotary,
    uidrIndexPercent,
    marginPercent,
  ]);

  const thumb = listing.images?.[0] ?? null;
  const priceLabel = formatListingPrice(
    listing.price,
    listing.currency,
    displayCurrency,
    listing.source_data,
  );
  const priceUahLabel = formatMoneyUah(carPriceUah);

  const handleSubmitApplication = async (e: React.FormEvent) => {
    e.preventDefault();
    const trimmedName = name.trim();
    if (trimmedName.length < 2) {
      setSubmitError("Вкажіть ім'я");
      return;
    }
    const normalized = normalizePhoneForApi(phone);
    if (normalized.length !== 12) {
      setSubmitError("Вкажіть номер телефону");
      return;
    }
    if (!quote.loanValid) {
      setSubmitError("Неможливо надіслати заявку для цих параметрів кредиту");
      return;
    }

    setSubmitting(true);
    setSubmitError("");
    try {
      await creditLeads.submit({
        name: trimmedName,
        phone: normalized,
        listing_id: listing.id,
        listing_title: listing.title,
        listing_url: listing.url ?? null,
        car_price_uah: quote.carPriceUah,
        down_payment_percent: quote.downPaymentPercent,
        term_months: quote.termMonths,
        loan_amount_uah: quote.loanAmountUah,
        monthly_payment_uah: quote.monthlyPaymentUah,
        monthly_payment_from_month2_uah: quote.monthlyPaymentFromMonth2Uah,
        registration_mode: quote.registrationMode,
        nominal_rate_percent: quote.nominalRatePercent,
        real_annual_rate_percent: quote.realAnnualRatePercent,
        total_repayment_uah: quote.totalRepaymentUah,
        one_time_fee_uah: quote.oneTimeFeeUah,
        notary_fee_uah: quote.notaryFeeUah,
      });
      setSubmitOk(true);
    } catch (err) {
      setSubmitError(err instanceof ApiError ? err.message : "Не вдалося надіслати заявку");
    } finally {
      setSubmitting(false);
    }
  };

  if (!open || typeof document === "undefined") return null;

  return createPortal(
    <>
    <div
      className="fixed inset-0 z-[135] flex items-end justify-center p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="credit-calc-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-ink/60 backdrop-blur-sm"
        aria-label="Закрити"
        onClick={onClose}
      />

      <div className="relative z-10 flex h-[min(700px,92dvh)] w-full max-w-[500px] flex-col overflow-hidden rounded-t-2xl border border-border/50 bg-white shadow-2xl sm:h-[min(740px,90vh)] sm:rounded-2xl">
        <div className="shrink-0 border-b border-border/40 px-4 py-3 sm:px-5">
          <div className="relative flex items-center justify-center">
            <Link
              href={BANK_PARTNER_BIZBANK.href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex shrink-0 rounded focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald"
              aria-label={BANK_PARTNER_BIZBANK.alt}
            >
              <Image
                src={BANK_PARTNER_BIZBANK.src}
                alt=""
                width={4147}
                height={942}
                aria-hidden
                className="h-5 w-auto max-w-[128px] object-contain sm:h-[22px]"
              />
            </Link>
            <div className="absolute right-0 top-1/2 flex -translate-y-1/2 items-center gap-0.5">
              <button
                type="button"
                onClick={() => setDisclaimerOpen(true)}
                aria-haspopup="dialog"
                className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink"
                aria-label="Інформація про розрахунок"
              >
                <IconInfo size={16} aria-hidden />
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink"
                aria-label="Закрити"
              >
                <IconX size={16} />
              </button>
            </div>
          </div>

          <div className="mt-3 flex gap-3">
            <div className="relative aspect-[4/3] w-[9.5rem] shrink-0 overflow-hidden rounded-2xl bg-surface sm:w-44">
              <ListingPhoto
                src={thumb}
                alt=""
                sizes="176px"
                priority
                logoClassName="h-8 w-8"
                className="h-full w-full"
                imageClassName="!object-contain"
              />
            </div>
            <div className="min-w-0 flex-1 self-center">
              <h2
                id="credit-calc-title"
                className="line-clamp-2 text-[15px] font-semibold leading-snug text-ink sm:text-[16px]"
              >
                {listing.title}
              </h2>
              <p className="mt-1 text-[18px] font-bold tabular-nums leading-tight text-ink sm:text-[20px]">
                {priceLabel}
                {displayCurrency !== "UAH" ? (
                  <span className="ml-1.5 text-[12px] font-normal text-ink/75">≈ {priceUahLabel}</span>
                ) : null}
              </p>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4 sm:px-5">
          <div className="space-y-3.5">
              <div
                className="flex rounded-xl bg-surface p-1"
                role="group"
                aria-label="Режим реєстрації"
              >
                  <button
                    type="button"
                    className={cn(
                      "flex-1 rounded-lg px-3 py-2 text-[13px] font-semibold leading-tight transition-colors",
                      registrationMode === "with_registration"
                        ? "bg-white text-ink shadow-sm"
                        : "text-ink/70 hover:text-ink",
                    )}
                    onClick={() => setRegistrationMode("with_registration")}
                  >
                    З реєстрацією
                  </button>
                  <button
                    type="button"
                    className={cn(
                      "flex-1 rounded-lg px-3 py-2 text-[13px] font-semibold leading-tight transition-colors",
                      registrationMode === "without_registration"
                        ? "bg-white text-ink shadow-sm"
                        : "text-ink/70 hover:text-ink",
                    )}
                    onClick={() => setRegistrationMode("without_registration")}
                  >
                    Без реєстрації
                  </button>
              </div>

              <CreditSlider
                id="credit-down"
                label="Перший внесок"
                valueLabel={`${formatMoneyUah(quote.downPaymentUah)} · ${formatPercentUk(quote.downPaymentPercent)}`}
                min={downMin}
                max={95}
                step={1}
                value={Math.max(downPercent, downMin)}
                onChange={setDownPercent}
                marks={[downMin, 50, 95]}
                formatMark={mark => `${mark}%`}
              />

              <CreditSlider
                id="credit-term"
                label="Строк кредитування"
                valueLabel={`${termMonths} міс.`}
                min={BISBANK_TERM_MIN_MONTHS}
                max={BISBANK_TERM_MAX_MONTHS}
                step={1}
                value={termMonths}
                onChange={setTermMonths}
                marks={BISBANK_TERM_MARKS}
                formatMark={(mark, max) => (mark === max ? `${mark} міс.` : String(mark))}
              />

              <div className="flex flex-wrap items-center gap-x-3 gap-y-1 px-0.5">
                <label className="inline-flex cursor-pointer items-center gap-1.5 text-[11px] leading-none text-ink/80">
                  <input
                    type="checkbox"
                    className="h-3 w-3 shrink-0 rounded border-border accent-emerald-dark"
                    checked={includeNotary}
                    onChange={e => setIncludeNotary(e.target.checked)}
                  />
                  <span>
                    Нотаріальні
                    <span className="text-ink/65"> · 0,12%</span>
                  </span>
                </label>
                <span className="text-[11px] text-ink/40" aria-hidden>
                  ·
                </span>
                <details className="group text-[11px] text-ink/80">
                  <summary className="cursor-pointer list-none marker:content-none [&::-webkit-details-marker]:hidden">
                    <span className="underline decoration-ink/25 underline-offset-2 group-open:text-ink group-open:no-underline">
                      UIDR з 25-го міс.
                    </span>
                  </summary>
                  <div className="mt-2 w-full min-w-[220px] space-y-1.5">
                    <p className="text-[10px] leading-snug text-ink/75">
                      Індекс + маржа (за замовч.{" "}
                      {formatPercentUk(BISBANK_FLOATING_MARGIN_DEFAULT * 100, 2)})
                    </p>
                    <div className="grid grid-cols-2 gap-1.5">
                      <label className="block">
                        <span className="text-[10px] text-ink/75">UIDR, %</span>
                        <input
                          type="text"
                          inputMode="decimal"
                          placeholder="0"
                          className="auth-input mt-0.5 w-full py-1 text-[11px]"
                          value={uidrIndexPercent}
                          onChange={e => setUidrIndexPercent(e.target.value)}
                        />
                      </label>
                      <label className="block">
                        <span className="text-[10px] text-ink/75">Маржа, %</span>
                        <input
                          type="text"
                          inputMode="decimal"
                          placeholder={formatPercentUk(BISBANK_FLOATING_MARGIN_DEFAULT * 100, 2).replace(
                            "%",
                            "",
                          )}
                          className="auth-input mt-0.5 w-full py-1 text-[11px]"
                          value={marginPercent}
                          onChange={e => setMarginPercent(e.target.value)}
                        />
                      </label>
                    </div>
                  </div>
                </details>
              </div>

            {quote.warnings.length > 0 ? (
              <ul className="space-y-1 rounded-xl bg-amber-50 px-3 py-2.5 text-[12px] leading-snug text-amber-900">
                {quote.warnings.map(w => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            ) : null}

            <div className="rounded-2xl bg-surface/70 px-4 py-4">
              {quote.loanValid &&
              quote.registrationMode === "without_registration" &&
              quote.monthlyPaymentFromMonth2Uah != null &&
              quote.monthlyPaymentFromMonth2Uah !== quote.monthlyPaymentUah ? (
                <div className="flex items-end justify-between gap-3">
                  <div className="min-w-0">
                    <p className="text-[12px] text-ink/80">
                      1-й {formatMoneyUah(quote.monthlyPaymentUah)} · далі
                    </p>
                    <p className="mt-0.5 whitespace-nowrap text-[24px] font-bold tabular-nums leading-none tracking-tight text-ink">
                      {formatMoneyUah(quote.monthlyPaymentFromMonth2Uah)}
                      <span className="text-[13px] font-medium text-ink/70">/міс</span>
                    </p>
                  </div>
                  {quote.realAnnualRatePercent != null ? (
                    <p className="shrink-0 pb-0.5 text-right text-[12px] tabular-nums text-ink/80">
                      XIRR {formatPercentUk(quote.realAnnualRatePercent, 1)}
                    </p>
                  ) : null}
                </div>
              ) : (
                <div className="flex items-end justify-between gap-3">
                  <p className="min-h-[1.75rem] whitespace-nowrap text-[24px] font-bold tabular-nums leading-none tracking-tight text-ink">
                    {quote.loanValid ? (
                      <>
                        {formatMoneyUah(quote.monthlyPaymentUah)}
                        <span className="text-[13px] font-medium text-ink/70">/міс</span>
                      </>
                    ) : (
                      "—"
                    )}
                  </p>
                  {quote.loanValid && quote.realAnnualRatePercent != null ? (
                    <p className="shrink-0 pb-0.5 text-right text-[12px] tabular-nums text-ink/80">
                      XIRR {formatPercentUk(quote.realAnnualRatePercent, 1)}
                    </p>
                  ) : null}
                </div>
              )}
              {quote.loanValid ? (
                <div className="mt-3">
                  <button
                    type="button"
                    className="inline-flex items-center gap-1 text-[12px] font-medium text-ink/80 transition hover:text-ink"
                    aria-expanded={quoteDetailsOpen}
                    onClick={() => setQuoteDetailsOpen(open => !open)}
                  >
                    Детальніше
                    <span
                      className={cn(
                        "text-[9px] transition-transform",
                        quoteDetailsOpen && "rotate-180",
                      )}
                      aria-hidden
                    >
                      ▼
                    </span>
                  </button>
                  {quoteDetailsOpen ? (
                    <div className="mt-3 space-y-3 border-t border-border/50 pt-3">
                      <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[12px]">
                        <div>
                          <dt className="text-ink/75">Сума кредиту</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.loanAmountUah)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-ink/75">Номінальна ставка</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatPercentUk(quote.nominalRatePercent, 2)} річних
                            {quote.secondaryRatePercent != null
                              ? ` · з 2-го ${formatPercentUk(quote.secondaryRatePercent, 2)}`
                              : null}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-ink/75">Разова комісія</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.oneTimeFeeUah)}
                          </dd>
                        </div>
                        {quote.notaryFeeUah > 0 ? (
                          <div>
                            <dt className="text-ink/75">Нотаріальні</dt>
                            <dd className="font-semibold tabular-nums text-ink">
                              {formatMoneyUah(quote.notaryFeeUah)}
                            </dd>
                          </div>
                        ) : null}
                        <div className={quote.notaryFeeUah > 0 ? "" : "col-span-2 sm:col-span-1"}>
                          <dt className="text-ink/75">Загальна вартість кредиту</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.totalConsumerCostUah)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-ink/75">Чиста видача</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.netDisbursementUah)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-ink/75">Відсотки за строк</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.totalInterestUah)}
                          </dd>
                        </div>
                        {quote.maturityDate ? (
                          <div className="col-span-2">
                            <dt className="text-ink/75">Дата погашення (орієнт.)</dt>
                            <dd className="font-semibold text-ink">
                              {formatBisbankDateUk(quote.maturityDate)}
                            </dd>
                          </div>
                        ) : null}
                      </dl>

                      {quote.paymentSchedule.length > 0 ? (
                        <div>
                          <p className="text-[12px] font-medium text-ink/80">
                            Графік · {quote.paymentSchedule.length - 1} міс.
                          </p>
                          <BisbankPaymentScheduleTable
                            className="mt-1.5 max-h-[min(180px,30dvh)] overflow-y-auto"
                            schedule={quote.paymentSchedule}
                          />
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </div>
              ) : null}
            </div>

            {submitOk ? (
              <div className="rounded-xl bg-emerald-light/50 px-4 py-3 text-[13px] leading-snug text-emerald-dark">
                Заявку надіслано. Менеджер банку зв&apos;яжеться з вами.
              </div>
            ) : applicationOpen ? (
              <form onSubmit={e => void handleSubmitApplication(e)} className="space-y-3 rounded-2xl border border-border/60 bg-surface/40 p-4">
                <p className="text-[14px] font-semibold text-ink">Заявка</p>
                <input
                  type="text"
                  name="name"
                  autoComplete="name"
                  placeholder="Ім'я"
                  className="auth-input w-full py-2.5 text-[14px]"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                  minLength={2}
                />
                <PhoneInput value={phone} onChange={setPhone} disabled={submitting} />
                {submitError ? (
                  <p className="text-[12px] font-medium text-red-600">{submitError}</p>
                ) : null}
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    variant="emerald"
                    size="lg"
                    loading={submitting}
                    disabled={!quote.loanValid}
                    className="flex-1 rounded-full hover:translate-y-0"
                  >
                    Надіслати
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="lg"
                    className="rounded-full hover:translate-y-0"
                    onClick={() => setApplicationOpen(false)}
                    disabled={submitting}
                  >
                    Назад
                  </Button>
                </div>
              </form>
            ) : (
              <Button
                type="button"
                variant="emerald"
                size="xl"
                className="w-full rounded-full shadow-[0_10px_28px_-8px_rgba(16,185,129,0.55)] hover:shadow-[0_14px_36px_-10px_rgba(16,185,129,0.65)]"
                disabled={!quote.loanValid}
                onClick={() => setApplicationOpen(true)}
              >
                Залишити заявку
              </Button>
            )}

            <p className="text-center">
              <Link
                href={BANK_PARTNER_BIZBANK.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[12px] font-medium text-ink/75 underline-offset-2 hover:text-ink hover:underline"
              >
                Умови банку
              </Link>
            </p>
          </div>
        </div>
      </div>
    </div>

    {disclaimerOpen ? (
      <div className="fixed inset-0 z-[145] flex items-end justify-center p-4 sm:items-center">
        <button
          type="button"
          className="absolute inset-0 bg-ink/50 backdrop-blur-[2px]"
          aria-label="Закрити"
          onClick={() => setDisclaimerOpen(false)}
        />
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="credit-calc-disclaimer-title"
          className="relative z-10 w-full max-w-[400px] overflow-hidden rounded-2xl border border-border/70 bg-white shadow-2xl"
          onClick={e => e.stopPropagation()}
        >
          <div className="flex items-start justify-between gap-3 border-b border-border/60 px-4 py-3 sm:px-5">
            <h3
              id="credit-calc-disclaimer-title"
              className="text-[15px] font-bold text-ink"
            >
              Про розрахунок
            </h3>
            <button
              type="button"
              onClick={() => setDisclaimerOpen(false)}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-border text-muted transition-colors hover:border-ink/20 hover:text-ink"
              aria-label="Закрити"
            >
              <IconX size={16} />
            </button>
          </div>
          <p className="max-h-[min(50dvh,320px)] overflow-y-auto px-4 py-4 text-[13px] leading-relaxed text-ink/75 sm:px-5">
            {CREDIT_CALC_DISCLAIMER}
          </p>
          <div className="border-t border-border/70 bg-surface/40 px-4 py-3 sm:px-5">
            <Button
              type="button"
              variant="emerald"
              size="md"
              className="w-full rounded-full hover:translate-y-0 sm:w-auto sm:min-w-[140px]"
              onClick={() => setDisclaimerOpen(false)}
            >
              Зрозуміло
            </Button>
          </div>
        </div>
      </div>
    ) : null}
    </>,
    document.body,
  );
}
