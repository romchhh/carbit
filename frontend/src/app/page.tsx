import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { HomeSearchSection } from "@/components/landing/HomeSearchSection";
import { HowItWorksCards } from "@/components/landing/HowItWorksCards";
import { LandingAbout } from "@/components/landing/LandingAbout";
import { LandingFaq } from "@/components/landing/LandingFaq";
import { VideoInstructions } from "@/components/landing/VideoInstructions";
import { PricingPlans } from "@/components/pricing/PricingPlans";
import { CtaLink } from "@/components/ui/CtaLink";
import { IconCheck } from "@/components/icons";
import { JsonLd } from "@/components/seo/JsonLd";
import { BANK_PARTNER_BIZBANK, LANDING_IMAGES, SOURCE_LOGOS } from "@/lib/brand-assets";
import {
  HOME_DESCRIPTION,
  HOME_TITLE,
  pageMetadata,
} from "@/lib/site-metadata";
import { faqJsonLd, homeWebPageJsonLd, videoObjectJsonLd } from "@/lib/structured-data";

export const metadata: Metadata = pageMetadata(HOME_TITLE, HOME_DESCRIPTION, {
  alternates: { canonical: "/" },
});

const SOURCE_LOGO_ROW = [
  { src: SOURCE_LOGOS.autoRia, alt: "AUTO.RIA — оголошення авто" },
  { src: SOURCE_LOGOS.olx, alt: "OLX — продаж авто" },
  { src: SOURCE_LOGOS.imperiya, alt: "Імперія Авто" },
  { src: SOURCE_LOGOS.udrive, alt: "uDrive" },
  { src: SOURCE_LOGOS.telegram, alt: "Telegram — канали авторинку" },
] as const;

export default function HomePage() {
  return (
    <>
      <JsonLd data={[homeWebPageJsonLd(), faqJsonLd(), videoObjectJsonLd()]} />
      <Header />
      <main className="bg-white">

        {/* ── HERO ─────────────────────────────────────────── */}
        <section
          id="landing-hero"
          className="relative flex h-[100dvh] max-h-[100dvh] flex-col overflow-hidden pt-[72px] sm:pt-[80px]"
        >
          <Image
            src={LANDING_IMAGES.hero}
            alt="Пошук авто на AUTO.RIA, OLX і Telegram — Carbit"
            fill
            priority
            className="object-cover object-center sm:scale-105"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-ink/95 via-ink/80 to-ink/50" />
          <div className="absolute inset-0 bg-gradient-to-t from-ink/60 via-transparent to-transparent" />

          <div className="absolute top-1/4 right-[15%] w-48 h-48 sm:w-72 sm:h-72 bg-emerald/20 rounded-full blur-[100px] pointer-events-none hidden sm:block motion-safe:animate-float" />
          <div className="absolute bottom-1/4 left-[10%] w-32 h-32 sm:w-48 sm:h-48 bg-emerald/10 rounded-full blur-[80px] pointer-events-none hidden sm:block" />

          <div className="relative flex min-h-0 flex-1 flex-col section-wrap w-full py-3 pb-4 sm:justify-center sm:py-8">
            <div className="flex min-h-0 flex-1 w-full max-w-[720px] flex-col justify-between gap-3 sm:min-h-0 sm:flex-none sm:justify-start sm:gap-0">
              <div className="min-h-0 shrink-0">
                <h1 className="w-full text-[clamp(1.65rem,5.2vw+0.35rem,4rem)] font-semibold leading-[1.1] tracking-[-0.015em] text-white animate-fade-up sm:leading-[1.12]">
                  <span className="block sm:whitespace-nowrap">Весь авторинок</span>
                  <span className="block sm:whitespace-nowrap">в одному місці</span>
                </h1>

                <p className="mt-3 max-w-[28rem] text-[14px] leading-snug text-white/65 animate-fade-up-delay sm:mt-5 sm:text-[17px]">
                  Моніторинг оголошень з миттєвим сповіщенням
                </p>

                <div className="mt-4 animate-fade-up-delay sm:mt-8">
                  <CtaLink
                    href="/auth/login"
                    variant="emerald"
                    size="lg"
                    className="!px-6 !py-3 !text-[14px] sm:!px-4 sm:!py-2 sm:!text-[13px]"
                  >
                    Спробувати «Старт» 7 днів
                  </CtaLink>
                </div>
              </div>

              <div className="shrink-0 pt-2 sm:pt-10">
                <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-white/35 sm:text-[11px]">
                  Джерела оголошень
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1.5 sm:mt-3 sm:gap-x-3">
                  <div className="inline-flex shrink-0 items-center">
                    {SOURCE_LOGO_ROW.map(({ src, alt }, index) => (
                      <span
                        key={alt}
                        className={cn(
                          "relative inline-flex h-9 w-9 sm:h-14 sm:w-14 shrink-0 overflow-hidden rounded-full bg-white shadow-md ring-2 ring-white/20",
                          index > 0 && "-ml-3 sm:-ml-4",
                        )}
                        style={{ zIndex: index + 1 }}
                        title={alt}
                      >
                        <Image
                          src={src}
                          alt={alt}
                          width={56}
                          height={56}
                          className="h-full w-full object-cover"
                        />
                      </span>
                    ))}
                  </div>
                  <span className="shrink-0 text-[11px] font-medium text-white/45 sm:text-[13px]">
                    та інші
                  </span>
                </div>

                <div className="mt-3 sm:mt-4">
                  <p className="text-[10px] font-medium uppercase tracking-[0.14em] text-white/35 sm:text-[11px]">
                    Банк-партнер
                  </p>
                  <a
                    href={BANK_PARTNER_BIZBANK.href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="group mt-1.5 inline-flex rounded-lg border border-white/10 bg-white/[0.04] px-3 py-2.5 transition hover:border-white/20 hover:bg-white/[0.07] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald sm:mt-2 sm:px-3.5 sm:py-3"
                    aria-label={BANK_PARTNER_BIZBANK.alt}
                  >
                    <Image
                      src={BANK_PARTNER_BIZBANK.logoWhiteSrc}
                      alt=""
                      width={1077}
                      height={245}
                      aria-hidden
                      className="h-[26px] w-auto max-w-[min(calc(100vw-3.5rem),420px)] object-contain object-left opacity-95 transition group-hover:opacity-100 sm:h-[34px] sm:max-w-[460px]"
                    />
                  </a>
                </div>

                <div className="mt-3 border-t border-white/10 pt-3 sm:mt-5 sm:pt-5">
                  <div className="grid grid-cols-4 gap-1 sm:gap-4">
                  {[
                    { value: "100+", label: "джерел" },
                    { value: "1 500+", label: "оголошень" },
                    { value: "< 5 хв", label: "до сповіщення" },
                    { value: "7 днів", label: "«Старт» free" },
                  ].map(({ value, label }) => (
                    <div key={label} className="min-w-0 text-center">
                      <div className="text-[12px] font-semibold leading-none text-white/60 sm:text-xl sm:text-white/80">
                        {value}
                      </div>
                      <div className="mt-0.5 text-[9px] leading-tight text-white/40 sm:mt-1.5 sm:text-[11px] sm:text-white/45">
                        {label}
                      </div>
                    </div>
                  ))}
                </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <HomeSearchSection />

        <HowItWorksCards />

        <LandingAbout />

        <LandingFaq />

        {/* ── VIDEO INSTRUCTIONS ───────────────────────────── */}
        <section className="bg-white section-y" aria-labelledby="video-heading">
          <div className="section-wrap">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
              <div>
                <h2
                  id="video-heading"
                  className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] leading-tight text-ink"
                >
                  Перестань гаяти час на ручний пошук авто
                </h2>
                <div className="mt-5 sm:mt-6 space-y-3">
                  {[
                    "Не витрачаєш годин на моніторинг AUTO.RIA, OLX і Telegram",
                    "Знаєш ринкову ціну до першого дзвінка",
                    "Отримуєш сигнал «брати/торгуватись» на даних",
                    "Не пропускаєш вигідні авто через запізнення",
                  ].map(t => (
                    <div key={t} className="flex items-start gap-3">
                      <IconCheck size={18} className="text-emerald shrink-0 mt-0.5"/>
                      <span className="text-[14px] text-ink leading-snug">{t}</span>
                    </div>
                  ))}
                </div>
                <div className="mt-6 sm:mt-8">
                  <CtaLink href="/auth/login" variant="emerald" size="lg">
                    Почати безкоштовно
                  </CtaLink>
                </div>
              </div>

              <VideoInstructions />
            </div>
          </div>
        </section>

        {/* ── PRICING ──────────────────────────────────────── */}
        <section className="bg-white section-y" aria-labelledby="pricing-heading">
          <div className="section-wrap">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-8 sm:mb-10">
              <h2
                id="pricing-heading"
                className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] text-ink"
              >
                Тарифи на моніторинг авто
              </h2>
              <Link href="/pricing" className="inline-flex items-center gap-1.5 text-[12px] text-muted hover:text-emerald-dark transition-colors group">
                Детальне порівняння тарифів
                <span className="w-6 h-6 rounded-full border border-border flex items-center justify-center group-hover:bg-emerald group-hover:border-emerald group-hover:text-white transition-all text-[11px]">
                  →
                </span>
              </Link>
            </div>

            <PricingPlans variant="home" />
          </div>
        </section>

        {/* ── CTA BANNER ───────────────────────────────────── */}
        <section className="bg-white section-y">
          <div className="section-wrap">
            <div className="relative bg-ink rounded-2xl sm:rounded-3xl px-6 sm:px-10 py-8 sm:py-10 overflow-hidden flex flex-col lg:flex-row items-center justify-between gap-6">
              <div className="absolute top-0 right-0 w-64 h-64 bg-emerald/15 rounded-full blur-[100px] pointer-events-none" />

              <div className="relative max-w-[480px] text-center lg:text-left">
                <h2 className="text-[26px] sm:text-[32px] font-semibold text-white tracking-[-0.02em] leading-tight">
                  Починай пошук авто швидше за ринок
                </h2>
                <p className="mt-2 text-[13px] text-white/50">
                  Без прив&apos;язки карти. 7 днів «Старт» після реєстрації, потім — Free (1 моніторинг).
                </p>
              </div>
              <CtaLink href="/auth/login" variant="emerald" size="lg" className="relative shrink-0">
                Почати безкоштовно
              </CtaLink>
            </div>
          </div>
        </section>

      </main>

      <Footer />
    </>
  );
}
