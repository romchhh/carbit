"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { IconX } from "@/components/icons";
import { ListingPhoto } from "@/components/listings/ListingPhoto";
import { BANK_PARTNER_BIZBANK } from "@/lib/brand-assets";
import {
  BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT,
  BISBANK_DEFAULT_TERM_MONTHS,
  BISBANK_TERM_MARKS,
  BISBANK_TERM_MAX_MONTHS,
  BISBANK_TERM_MIN_MONTHS,
  computeBisbankCreditQuote,
  formatMoneyUah,
  formatPercentUk,
  minDownPaymentPercent,
  resolveListingPriceUah,
} from "@/lib/bisbank-credit-calculator";
import { formatListingPrice, type DisplayCurrency } from "@/lib/display-currency";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import type { Listing } from "@/types/api";

type Props = {
  open: boolean;
  listing: Listing;
  displayCurrency: DisplayCurrency;
  onClose: () => void;
};

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
}) {
  return (
    <div>
      <div className="flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-[13px] font-medium text-ink">
          {label}
        </label>
        <span className="text-[13px] font-semibold tabular-nums text-ink">{valueLabel}</span>
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
        <div className="mt-1.5 flex justify-between text-[10px] tabular-nums text-muted">
          {marks.map(mark => (
            <span key={mark}>{mark === max ? `${mark} міс.` : mark}</span>
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
  const carPriceUah = resolveListingPriceUah(listing);
  const minDown = minDownPaymentPercent(carPriceUah);
  const downMin = Math.max(10, Math.ceil(minDown));

  const [downPercent, setDownPercent] = useState(() =>
    Math.max(BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT, downMin),
  );
  const [termMonths, setTermMonths] = useState(BISBANK_DEFAULT_TERM_MONTHS);

  useEffect(() => {
    if (!open) return;
    setDownPercent(prev => Math.max(prev, downMin, BISBANK_DEFAULT_DOWN_PAYMENT_PERCENT));
    setTermMonths(BISBANK_DEFAULT_TERM_MONTHS);
  }, [open, listing.id, downMin]);

  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  const quote = useMemo(
    () =>
      computeBisbankCreditQuote({
        carPriceUah,
        downPaymentPercent: downPercent,
        termMonths,
      }),
    [carPriceUah, downPercent, termMonths],
  );

  const thumb = listing.images?.[0] ?? null;
  const priceLabel = formatListingPrice(
    listing.price,
    listing.currency,
    displayCurrency,
    listing.source_data,
  );
  const priceUahLabel = formatMoneyUah(carPriceUah);

  if (!open) return null;

  return (
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

      <div className="relative z-10 flex max-h-[92dvh] w-full max-w-[480px] flex-col overflow-hidden rounded-t-[1.5rem] border border-border/60 bg-white shadow-2xl sm:max-h-[90vh] sm:rounded-[1.5rem]">
        <div className="flex items-start justify-between gap-3 border-b border-border/60 px-5 py-4">
          <div>
            <h2 id="credit-calc-title" className="text-[18px] font-bold tracking-[-0.02em] text-ink">
              Калькулятор кредиту
            </h2>
            <p className="mt-0.5 text-[12px] text-muted">Орієнтовний розрахунок · банк-партнер</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border text-muted transition-colors hover:border-ink/20 hover:text-ink"
            aria-label="Закрити"
          >
            <IconX size={18} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-4">
          <div className="flex gap-3 rounded-2xl border border-border/70 bg-surface/60 p-3">
            <div className="relative h-16 w-24 shrink-0 overflow-hidden rounded-xl bg-surface">
              <ListingPhoto
                src={thumb}
                alt={listing.title}
                sizes="96px"
                logoClassName="h-6"
              />
            </div>
            <div className="min-w-0 flex-1">
              <p className="line-clamp-2 text-[14px] font-semibold leading-snug text-ink">
                {listing.title}
              </p>
              <p className="mt-1 text-[17px] font-bold text-emerald-dark">{priceLabel}</p>
              {displayCurrency !== "UAH" ? (
                <p className="text-[12px] text-muted">≈ {priceUahLabel}</p>
              ) : null}
            </div>
          </div>

          <div className="mt-5 space-y-5">
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
            />
          </div>

          {quote.warnings.length > 0 ? (
            <ul className="mt-4 space-y-1.5 rounded-xl border border-amber-200/80 bg-amber-50 px-3 py-2.5 text-[12px] leading-snug text-amber-900">
              {quote.warnings.map(w => (
                <li key={w}>{w}</li>
              ))}
            </ul>
          ) : null}

          <div className="mt-5 rounded-2xl border border-emerald/25 bg-emerald-light/40 p-4">
            <p className="text-[12px] font-medium uppercase tracking-wide text-emerald-dark/80">
              Орієнтовний платіж
            </p>
            <p className="mt-1 text-[28px] font-bold tabular-nums tracking-tight text-emerald-dark">
              {quote.loanValid ? `${formatMoneyUah(quote.monthlyPaymentUah)}/міс.` : "—"}
            </p>
            {quote.loanValid ? (
              <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-[12px]">
                <div>
                  <dt className="text-muted">Сума кредиту</dt>
                  <dd className="font-semibold tabular-nums text-ink">
                    {formatMoneyUah(quote.loanAmountUah)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Ставка</dt>
                  <dd className="font-semibold tabular-nums text-ink">
                    {formatPercentUk(quote.annualRatePercent, 2)} річних
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Разова комісія</dt>
                  <dd className="font-semibold tabular-nums text-ink">
                    {formatMoneyUah(quote.oneTimeFeeUah)}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted">Разом за строк</dt>
                  <dd className="font-semibold tabular-nums text-ink">
                    {formatMoneyUah(quote.totalRepaymentUah)}
                  </dd>
                </div>
              </dl>
            ) : null}
          </div>

          <div className="mt-4 flex items-center justify-between gap-3 rounded-xl border border-border/70 bg-white px-3 py-2.5">
            <Link
              href={BANK_PARTNER_BIZBANK.href}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex min-w-0 items-center"
            >
              <Image
                src={BANK_PARTNER_BIZBANK.src}
                alt={BANK_PARTNER_BIZBANK.alt}
                width={4147}
                height={942}
                className="h-6 w-auto max-w-[140px] object-contain"
              />
            </Link>
            <Link
              href={BANK_PARTNER_BIZBANK.href}
              target="_blank"
              rel="noopener noreferrer"
              className="shrink-0 text-[12px] font-semibold text-emerald-dark hover:underline"
            >
              Деталі на сайті банку
            </Link>
          </div>

          <p className="mt-3 text-[11px] leading-relaxed text-muted">
            Розрахунок за методикою калькулятора БІЗБАНК (ануїтет, фіксована ставка). Не є
            публічною офертою; фактичні умови залежать від рішення банку та документів на авто.
          </p>
        </div>
      </div>
    </div>
  );
}
