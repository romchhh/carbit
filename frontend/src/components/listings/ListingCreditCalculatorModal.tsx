"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
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
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-[12px] font-medium text-ink">
          {label}
        </label>
        <span className="text-[12px] font-semibold tabular-nums text-ink">{valueLabel}</span>
      </div>
      <input
        id={id}
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="credit-slider mt-2 w-full"
      />
      {marks && marks.length > 0 ? (
        <div className="mt-1.5 flex justify-between text-[10px] tabular-nums text-muted">
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

  const quote = useMemo(() => {
    const uidr = parseFloat(uidrIndexPercent.replace(",", "."));
    const margin = parseFloat(marginPercent.replace(",", "."));
    return computeBisbankCreditQuote({
      carPriceUah,
      downPaymentPercent: downPercent,
      termMonths,
      registrationMode,
      options: {
        includeNotaryFee: includeNotary,
        uidrIndex: Number.isFinite(uidr) ? uidr / 100 : 0,
        margin: Number.isFinite(margin) ? margin / 100 : 0,
      },
    });
  }, [
    carPriceUah,
    downPercent,
    termMonths,
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

  if (!open) return null;

  return (
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

      <div className="relative z-10 flex max-h-[92dvh] w-full max-w-[520px] flex-col overflow-hidden rounded-t-[1.5rem] border border-border/60 bg-white shadow-2xl sm:max-h-[90vh] sm:rounded-[1.5rem]">
        <div className="shrink-0 border-b border-border/60 px-4 py-3 sm:px-5">
          <div className="flex items-start gap-2">
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
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
                    className="h-5 w-auto max-w-[120px] object-contain sm:h-6 sm:max-w-[140px]"
                  />
                </Link>
                <h2
                  id="credit-calc-title"
                  className="text-[14px] font-bold tracking-[-0.02em] text-ink sm:text-[15px]"
                >
                  Калькулятор кредиту
                </h2>
                <span className="text-[11px] text-muted">· орієнтовно</span>
              </div>

              <div className="mt-2 flex gap-2.5">
                <div className="relative h-12 w-12 shrink-0 overflow-hidden rounded-lg border border-border/60 bg-surface sm:h-14 sm:w-14 sm:rounded-xl">
                  <ListingPhoto
                    src={thumb}
                    alt=""
                    sizes="56px"
                    priority
                    logoClassName="h-5 w-5"
                    className="h-full w-full"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <h3 className="line-clamp-2 text-[13px] font-semibold leading-snug text-ink">
                    {listing.title}
                  </h3>
                  <p className="mt-0.5 text-[16px] font-bold leading-tight tabular-nums text-emerald-dark sm:text-[17px]">
                    {priceLabel}
                    {displayCurrency !== "UAH" ? (
                      <span className="ml-1.5 text-[11px] font-medium text-muted">
                        ≈ {priceUahLabel}
                      </span>
                    ) : null}
                  </p>
                </div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-1">
              <button
                type="button"
                onClick={() => setDisclaimerOpen(true)}
                aria-haspopup="dialog"
                className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted transition-colors hover:border-ink/20 hover:text-ink"
                aria-label="Інформація про розрахунок"
              >
                <IconInfo size={16} aria-hidden />
              </button>
              <button
                type="button"
                onClick={onClose}
                className="flex h-8 w-8 items-center justify-center rounded-full border border-border text-muted transition-colors hover:border-ink/20 hover:text-ink"
                aria-label="Закрити"
              >
                <IconX size={16} />
              </button>
            </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-3 sm:px-5 sm:py-4">
          <div className="space-y-4">
              <div>
                <p className="text-[12px] font-medium text-muted">Реєстрація ТЗ</p>
                <div
                  className="mt-1.5 flex rounded-full border border-border/80 bg-surface/80 p-0.5"
                  role="group"
                  aria-label="Режим реєстрації"
                >
                  <button
                    type="button"
                    className={cn(
                      "flex-1 rounded-full px-2 py-1.5 text-[11px] font-semibold leading-tight transition-colors",
                      registrationMode === "with_registration"
                        ? "bg-white text-ink shadow-sm"
                        : "text-muted hover:text-ink",
                    )}
                    onClick={() => setRegistrationMode("with_registration")}
                  >
                    З реєстрацією
                  </button>
                  <button
                    type="button"
                    className={cn(
                      "flex-1 rounded-full px-2 py-1.5 text-[11px] font-semibold leading-tight transition-colors",
                      registrationMode === "without_registration"
                        ? "bg-white text-ink shadow-sm"
                        : "text-muted hover:text-ink",
                    )}
                    onClick={() => setRegistrationMode("without_registration")}
                  >
                    Без реєстрації
                  </button>
                </div>
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

              <div className="space-y-2 rounded-lg border border-border/70 bg-surface/40 px-2.5 py-2">
                <label className="flex cursor-pointer items-center gap-2 text-[12px] leading-snug text-ink">
                  <input
                    type="checkbox"
                    className="h-3.5 w-3.5 shrink-0 rounded border-border accent-emerald-dark"
                    checked={includeNotary}
                    onChange={e => setIncludeNotary(e.target.checked)}
                  />
                  <span>
                    Нотаріальні послуги
                    <span className="text-muted"> · 0,12%×сума×строк</span>
                  </span>
                </label>

                <details className="group text-[11px] text-ink">
                  <summary className="cursor-pointer list-none font-medium text-emerald-dark marker:content-none [&::-webkit-details-marker]:hidden">
                    <span className="underline decoration-emerald/30 underline-offset-2 group-open:no-underline">
                      UIDR з 25-го місяця
                    </span>
                  </summary>
                  <p className="mt-1.5 text-[10px] leading-snug text-muted">
                    Ставка = індекс + маржа (за замовч. маржа{" "}
                    {formatPercentUk(BISBANK_FLOATING_MARGIN_DEFAULT * 100, 2)}).
                  </p>
                  <div className="mt-1.5 grid grid-cols-2 gap-1.5">
                    <label className="block">
                      <span className="text-[10px] text-muted">UIDR, %</span>
                      <input
                        type="text"
                        inputMode="decimal"
                        placeholder="0"
                        className="auth-input mt-0.5 w-full py-1.5 text-[12px]"
                        value={uidrIndexPercent}
                        onChange={e => setUidrIndexPercent(e.target.value)}
                      />
                    </label>
                    <label className="block">
                      <span className="text-[10px] text-muted">Маржа, %</span>
                      <input
                        type="text"
                        inputMode="decimal"
                        placeholder={formatPercentUk(BISBANK_FLOATING_MARGIN_DEFAULT * 100, 2).replace(
                          "%",
                          "",
                        )}
                        className="auth-input mt-0.5 w-full py-1.5 text-[12px]"
                        value={marginPercent}
                        onChange={e => setMarginPercent(e.target.value)}
                      />
                    </label>
                  </div>
                </details>
              </div>

            {quote.warnings.length > 0 ? (
              <ul className="mt-3 space-y-1 rounded-lg border border-amber-200/80 bg-amber-50 px-2.5 py-2 text-[11px] leading-snug text-amber-900">
                {quote.warnings.map(w => (
                  <li key={w}>{w}</li>
                ))}
              </ul>
            ) : null}

            <div className="mt-3 rounded-xl border border-emerald/25 bg-emerald-light/40 px-3 py-2.5">
              <p className="text-[10px] font-medium uppercase tracking-wide text-emerald-dark/75">
                Орієнтовний платіж
              </p>
              {quote.loanValid &&
              quote.registrationMode === "without_registration" &&
              quote.monthlyPaymentFromMonth2Uah != null &&
              quote.monthlyPaymentFromMonth2Uah !== quote.monthlyPaymentUah ? (
                <div className="mt-0.5 space-y-0.5">
                  <p className="text-[13px] font-semibold tabular-nums text-emerald-dark">
                    1-й: {formatMoneyUah(quote.monthlyPaymentUah)}
                  </p>
                  <p className="text-[22px] font-bold tabular-nums leading-tight tracking-tight text-emerald-dark">
                    з 2-го: {formatMoneyUah(quote.monthlyPaymentFromMonth2Uah)}/міс.
                  </p>
                </div>
              ) : (
                <p className="mt-0.5 text-[22px] font-bold tabular-nums leading-tight tracking-tight text-emerald-dark">
                  {quote.loanValid ? `${formatMoneyUah(quote.monthlyPaymentUah)}/міс.` : "—"}
                </p>
              )}
              {quote.loanValid && quote.realAnnualRatePercent != null ? (
                <p className="mt-1 text-[11px] leading-snug text-emerald-dark/85">
                  Реальна ставка ≈{" "}
                  <span className="font-bold tabular-nums">
                    {formatPercentUk(quote.realAnnualRatePercent, 1)}
                  </span>
                  <span className="text-muted"> · XIRR</span>
                </p>
              ) : null}
              {quote.loanValid ? (
                <div className="mt-2 border-t border-emerald/15 pt-2">
                  <button
                    type="button"
                    className="flex w-full items-center justify-between gap-2 py-0.5 text-left text-[12px] font-semibold text-emerald-dark transition hover:text-emerald-dark/90"
                    aria-expanded={quoteDetailsOpen}
                    onClick={() => setQuoteDetailsOpen(open => !open)}
                  >
                    <span>Детальніше</span>
                    <span
                      className={cn(
                        "text-[10px] text-muted transition-transform",
                        quoteDetailsOpen && "rotate-180",
                      )}
                      aria-hidden
                    >
                      ▼
                    </span>
                  </button>
                  {quoteDetailsOpen ? (
                    <div className="mt-2 space-y-3">
                      <dl className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-[11px]">
                        <div>
                          <dt className="text-muted">Сума кредиту</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.loanAmountUah)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted">Номінальна ставка</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatPercentUk(quote.nominalRatePercent, 2)} річних
                            {quote.secondaryRatePercent != null
                              ? ` · з 2-го ${formatPercentUk(quote.secondaryRatePercent, 2)}`
                              : null}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted">Разова комісія</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.oneTimeFeeUah)}
                          </dd>
                        </div>
                        {quote.notaryFeeUah > 0 ? (
                          <div>
                            <dt className="text-muted">Нотаріальні</dt>
                            <dd className="font-semibold tabular-nums text-ink">
                              {formatMoneyUah(quote.notaryFeeUah)}
                            </dd>
                          </div>
                        ) : null}
                        <div className={quote.notaryFeeUah > 0 ? "" : "col-span-2 sm:col-span-1"}>
                          <dt className="text-muted">Загальна вартість кредиту</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.totalConsumerCostUah)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted">Чиста видача</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.netDisbursementUah)}
                          </dd>
                        </div>
                        <div>
                          <dt className="text-muted">Відсотки за строк</dt>
                          <dd className="font-semibold tabular-nums text-ink">
                            {formatMoneyUah(quote.totalInterestUah)}
                          </dd>
                        </div>
                        {quote.maturityDate ? (
                          <div className="col-span-2">
                            <dt className="text-muted">Дата погашення (орієнт.)</dt>
                            <dd className="font-semibold text-ink">
                              {formatBisbankDateUk(quote.maturityDate)}
                            </dd>
                          </div>
                        ) : null}
                      </dl>

                      {quote.paymentSchedule.length > 0 ? (
                        <div>
                          <p className="text-[11px] font-semibold text-ink">
                            Графік ({quote.paymentSchedule.length - 1} міс.)
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

            <p className="mt-3 text-center">
              <Link
                href={BANK_PARTNER_BIZBANK.href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[12px] font-semibold text-emerald-dark hover:underline"
              >
                Умови на сайті банку
              </Link>
            </p>

            {submitOk ? (
              <div className="mt-4 rounded-xl border border-emerald/25 bg-emerald-light/50 px-4 py-3 text-[13px] leading-snug text-emerald-dark">
                Заявку надіслано. Менеджер банку-партнера зв&apos;яжеться з вами за вказаним номером.
              </div>
            ) : applicationOpen ? (
              <form onSubmit={e => void handleSubmitApplication(e)} className="mt-4 space-y-3 rounded-2xl border border-border/80 bg-surface/50 p-4">
                <p className="text-[14px] font-semibold text-ink">Залишити заявку</p>
                <p className="text-[12px] leading-snug text-muted">
                  Вкажіть контакти — передамо заявку з параметрами розрахунку банку-партнеру.
                </p>
                <input
                  type="text"
                  name="name"
                  autoComplete="name"
                  placeholder="Ім'я"
                  className="auth-input w-full"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  required
                  minLength={2}
                />
                <PhoneInput value={phone} onChange={setPhone} disabled={submitting} />
                {submitError ? (
                  <p className="text-[12px] font-medium text-red-600">{submitError}</p>
                ) : null}
                <div className="flex flex-col gap-2 sm:flex-row">
                  <Button
                    type="submit"
                    variant="emerald"
                    size="lg"
                    loading={submitting}
                    disabled={!quote.loanValid}
                    className="w-full flex-1 rounded-full hover:translate-y-0"
                  >
                    Надіслати заявку
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    size="lg"
                    className="w-full flex-1 rounded-full hover:translate-y-0"
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
                size="lg"
                className="mt-4 w-full rounded-full hover:translate-y-0"
                disabled={!quote.loanValid}
                onClick={() => setApplicationOpen(true)}
              >
                Залишити заявку
              </Button>
            )}
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
          <p className="max-h-[min(50dvh,320px)] overflow-y-auto px-4 py-4 text-[13px] leading-relaxed text-muted sm:px-5">
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
    </>
  );
}
