"use client";

import Image from "next/image";
import Link from "next/link";
import { useCallback, useEffect, useRef, useState } from "react";
import { FRESH_LISTINGS } from "@/data/freshListings";
import { Badge } from "@/components/ui/Badge";
import { IconArrowLeft, IconArrowRight } from "@/components/icons";
import { cn } from "@/lib/utils";

const sourceVariant = {
  Telegram: "emerald",
  "AUTO.RIA": "gray",
  OLX: "outline",
} as const;

export function FreshListingsCarousel() {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeIndex, setActiveIndex] = useState(0);

  const scrollToIndex = useCallback((index: number) => {
    const container = scrollRef.current;
    if (!container) return;

    const card = container.children[index] as HTMLElement | undefined;
    if (!card) return;

    container.scrollTo({ left: card.offsetLeft, behavior: "smooth" });
    setActiveIndex(index);
  }, []);

  useEffect(() => {
    const container = scrollRef.current;
    if (!container) return;

    const cards = Array.from(container.children) as HTMLElement[];
    if (!cards.length) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((e) => e.isIntersecting)
          .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

        if (!visible.length) return;

        const index = cards.indexOf(visible[0].target as HTMLElement);
        if (index >= 0) setActiveIndex(index);
      },
      { root: container, threshold: 0.55 }
    );

    cards.forEach((card) => observer.observe(card));
    return () => observer.disconnect();
  }, []);

  const canPrev = activeIndex > 0;
  const canNext = activeIndex < FRESH_LISTINGS.length - 1;

  return (
    <section id="fresh-listings" className="bg-white py-10 sm:py-12">
      <div className="max-w-[1280px] mx-auto px-5 sm:px-6">
        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-5">
          <div>
            <h2 className="text-[26px] sm:text-[32px] font-semibold tracking-[-0.02em] text-ink leading-tight">
              Свіжі пропозиції
            </h2>
            <p className="mt-1 text-[13px] sm:text-[14px] text-muted leading-snug max-w-[360px]">
              Оголошення, знайдені платформою за останню годину
            </p>
          </div>
          <Link
            href="/app/results"
            className="inline-flex items-center gap-1.5 text-[12px] font-medium text-muted hover:text-emerald-dark transition-colors shrink-0"
          >
            Усі результати
            <span className="text-emerald">→</span>
          </Link>
        </div>

        <div
          ref={scrollRef}
          className="flex gap-3 sm:gap-4 overflow-x-auto pb-2 -mx-5 pl-5 pr-8 sm:-mx-6 sm:px-6 snap-x snap-mandatory scrollbar-hide scroll-smooth"
        >
          {FRESH_LISTINGS.map((car) => (
            <article
              key={car.id}
              className="snap-start shrink-0 w-[272px] sm:w-[300px] bg-white rounded-2xl border border-border/70 overflow-hidden"
            >
              <div className="relative h-[152px] sm:h-[168px] bg-surface">
                <Image
                  src={car.image}
                  alt={car.title}
                  fill
                  className="object-cover"
                  sizes="300px"
                />
                <div className="absolute top-2.5 left-2.5 flex flex-wrap gap-1">
                  {car.isNew && <Badge variant="emerald" className="text-[10px] px-2 py-0.5">Нове</Badge>}
                  {car.priceDown && <Badge variant="red" className="text-[10px] px-2 py-0.5">↓ Ціна знижена</Badge>}
                </div>
              </div>

              <div className="p-4">
                <h3 className="text-[15px] font-semibold text-ink leading-tight truncate">{car.title}</h3>
                <p className="mt-2 text-[20px] font-semibold text-ink tracking-tight">{car.price}</p>
                <p className="mt-1.5 text-[12px] text-muted leading-snug">
                  {car.year} · {car.mileage} · {car.transmission} · {car.fuel}
                </p>
                <div className="mt-3 flex items-center justify-between gap-2">
                  <span className="text-[12px] text-muted truncate">{car.city}</span>
                  <Badge variant={sourceVariant[car.source]} className="text-[10px] px-2 py-0.5 shrink-0">
                    {car.source}
                  </Badge>
                </div>
              </div>
            </article>
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between gap-4">
          <div className="flex items-center gap-1.5 flex-wrap">
            {FRESH_LISTINGS.map((car, index) => (
              <button
                key={car.id}
                type="button"
                aria-label={`Перейти до оголошення ${index + 1}`}
                aria-current={activeIndex === index ? "true" : undefined}
                onClick={() => scrollToIndex(index)}
                className={cn(
                  "h-2 rounded-full transition-all duration-300",
                  activeIndex === index
                    ? "w-5 bg-emerald"
                    : "w-2 bg-border hover:bg-muted/60"
                )}
              />
            ))}
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <button
              type="button"
              aria-label="Попереднє оголошення"
              disabled={!canPrev}
              onClick={() => scrollToIndex(activeIndex - 1)}
              className={cn(
                "w-9 h-9 rounded-full border flex items-center justify-center transition-all duration-200",
                canPrev
                  ? "border-border text-ink hover:border-emerald hover:text-emerald hover:bg-emerald/5"
                  : "border-border/60 text-muted/40 cursor-not-allowed"
              )}
            >
              <IconArrowLeft size={16} />
            </button>
            <button
              type="button"
              aria-label="Наступне оголошення"
              disabled={!canNext}
              onClick={() => scrollToIndex(activeIndex + 1)}
              className={cn(
                "w-9 h-9 rounded-full border flex items-center justify-center transition-all duration-200",
                canNext
                  ? "border-border text-ink hover:border-emerald hover:text-emerald hover:bg-emerald/5"
                  : "border-border/60 text-muted/40 cursor-not-allowed"
              )}
            >
              <IconArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
}
