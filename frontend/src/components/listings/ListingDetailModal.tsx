"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { IconGlobe, IconX } from "@/components/icons";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import { formatMileage, formatPrice } from "@/lib/utils";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing | null;
  onClose: () => void;
};

export function ListingDetailModal({ listing, onClose }: Props) {
  const [photoIndex, setPhotoIndex] = useState(0);

  useEffect(() => {
    if (!listing) return;
    setPhotoIndex(0);
    lockBodyScroll();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [listing, onClose]);

  if (!listing) return null;

  const photos = listing.images.length ? listing.images : [];
  const activePhoto = photos[photoIndex] ?? photos[0];

  const specs = [
    { label: "Рік", value: listing.year ? String(listing.year) : "—" },
    { label: "Пробіг", value: listing.mileage ? formatMileage(listing.mileage) : "—" },
    { label: "Паливо", value: listing.fuel || "—" },
    { label: "КПП", value: listing.transmission || "—" },
    { label: "Регіон", value: listing.region || "—" },
    {
      label: "Продавець",
      value: listing.seller_type === "dealer" ? "Автосалон" : "Приват",
    },
  ];

  return (
    <div
      className="fixed inset-0 z-[120] flex items-end sm:items-center justify-center p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="listing-modal-title"
    >
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-ink/60"
        onClick={onClose}
      />

      <div className="relative z-10 flex max-h-[92dvh] w-full max-w-[720px] flex-col overflow-hidden rounded-t-[1.5rem] border border-border bg-white shadow-[0_24px_80px_-20px_rgba(10,12,14,0.35)] sm:rounded-[1.5rem]">
        <div className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-5">
          <div className="min-w-0 pr-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-muted">AUTO.RIA</p>
            <h2 id="listing-modal-title" className="truncate text-[16px] font-bold text-ink sm:text-[18px]">
              {listing.title}
            </h2>
          </div>
          <button
            type="button"
            aria-label="Закрити"
            onClick={onClose}
            className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-border text-muted transition-colors hover:bg-surface hover:text-ink"
          >
            <IconX size={18} />
          </button>
        </div>

        <div className="overflow-y-auto overscroll-contain">
          <div className="relative aspect-[16/10] w-full bg-surface">
            {activePhoto ? (
              <Image
                src={activePhoto}
                alt={listing.title}
                fill
                className="object-cover"
                sizes="720px"
                unoptimized
                priority
              />
            ) : (
              <div className="flex h-full items-center justify-center text-[13px] text-muted">
                Фото відсутнє
              </div>
            )}
          </div>

          {photos.length > 1 && (
            <div className="flex gap-2 overflow-x-auto border-b border-border px-4 py-3 sm:px-5">
              {photos.map((src, index) => (
                <button
                  key={`${src}-${index}`}
                  type="button"
                  onClick={() => setPhotoIndex(index)}
                  className={`relative h-14 w-20 shrink-0 overflow-hidden rounded-lg border-2 transition-colors ${
                    index === photoIndex ? "border-emerald" : "border-transparent"
                  }`}
                >
                  <Image src={src} alt="" fill className="object-cover" sizes="80px" unoptimized />
                </button>
              ))}
            </div>
          )}

          <div className="space-y-5 px-4 py-5 sm:px-6 sm:py-6">
            <div className="flex flex-wrap items-end justify-between gap-3">
              <div>
                <div className="text-[28px] font-black leading-none text-ink sm:text-[32px]">
                  {formatPrice(listing.price, listing.currency)}
                </div>
                <p className="mt-1.5 text-[12px] text-muted">
                  {listing.brand} {listing.model}
                </p>
              </div>
              <Badge variant="outline">AUTO.RIA</Badge>
            </div>

            <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
              {specs.map(({ label, value }) => (
                <div key={label} className="rounded-xl border border-border/70 bg-surface/60 px-3 py-2.5">
                  <div className="text-[10px] font-semibold uppercase tracking-wide text-muted">{label}</div>
                  <div className="mt-1 text-[13px] font-semibold text-ink">{value}</div>
                </div>
              ))}
            </div>

            {listing.description && (
              <div>
                <h3 className="text-[13px] font-bold text-ink">Опис</h3>
                <p className="mt-2 text-[13px] leading-relaxed text-muted">{listing.description}</p>
              </div>
            )}

            <div className="flex flex-col gap-2 pb-[max(0.5rem,env(safe-area-inset-bottom))] sm:flex-row sm:pb-0">
              <Link href={listing.url} target="_blank" rel="noopener noreferrer" className="flex-1">
                <Button variant="primary" size="md" className="w-full gap-1.5">
                  <IconGlobe size={14} />
                  Відкрити на AUTO.RIA
                </Button>
              </Link>
              <Button variant="secondary" size="md" className="sm:w-auto" onClick={onClose}>
                Закрити
              </Button>
            </div>

            <p className="text-center text-[11px] text-muted">
              Дані надано{" "}
              <a
                href="https://auto.ria.com"
                target="_blank"
                rel="noopener noreferrer"
                className="text-emerald-dark hover:underline"
              >
                AUTO.RIA
              </a>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
