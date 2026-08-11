import Image from "next/image";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { HomeSearchSection } from "@/components/landing/HomeSearchSection";
import { LandingFaq } from "@/components/landing/LandingFaq";
import { VideoInstructions } from "@/components/landing/VideoInstructions";
import { PricingPlans } from "@/components/pricing/PricingPlans";
import { CtaLink } from "@/components/ui/CtaLink";
import { IconCheck } from "@/components/icons";

import { LANDING_IMAGES, SOURCE_LOGOS } from "@/lib/brand-assets";

const PARTNER_LOGOS = [
  { src: SOURCE_LOGOS.autoRia, alt: "AUTO.RIA" },
  { src: SOURCE_LOGOS.olx, alt: "OLX" },
  { src: SOURCE_LOGOS.imperiya, alt: "Імперія Авто" },
  { src: SOURCE_LOGOS.telegram, alt: "Telegram" },
] as const;

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="bg-white">

        {/* ── HERO ─────────────────────────────────────────── */}
        <section id="landing-hero" className="relative min-h-[100dvh] flex items-start sm:items-center overflow-hidden pt-[72px] sm:pt-[80px]">
          <Image
            src={LANDING_IMAGES.hero}
            alt=""
            fill
            priority
            className="object-cover object-center sm:scale-105"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-ink/95 via-ink/80 to-ink/50" />
          <div className="absolute inset-0 bg-gradient-to-t from-ink/60 via-transparent to-transparent" />

          <div className="absolute top-1/4 right-[15%] w-48 h-48 sm:w-72 sm:h-72 bg-emerald/20 rounded-full blur-[100px] pointer-events-none hidden sm:block motion-safe:animate-float" />
          <div className="absolute bottom-1/4 left-[10%] w-32 h-32 sm:w-48 sm:h-48 bg-emerald/10 rounded-full blur-[80px] pointer-events-none hidden sm:block" />

          <div className="relative section-wrap w-full pt-10 pb-14 sm:py-20">
            <div className="flex w-full max-w-[720px] flex-col min-h-[calc(100dvh-10rem)] sm:min-h-0 pt-4 sm:pt-0">
              <h1 className="w-full text-[clamp(2.05rem,6.8vw+0.4rem,4rem)] font-semibold leading-[1.12] tracking-[-0.015em] text-white animate-fade-up">
                <span className="block sm:whitespace-nowrap">Знайди авто раніше</span>
                <span className="block sm:whitespace-nowrap">конкурентів</span>
              </h1>

              <div className="mt-7 w-full animate-fade-up-delay sm:mt-8">
                <p className="text-[18px] leading-relaxed text-white/90 sm:text-[21px] sm:leading-snug">
                  Миттєві сповіщення та моніторинг потрібної моделі
                </p>
              </div>

              <div className="mt-12 flex justify-start animate-fade-up-delay sm:mt-10">
                <CtaLink
                  href="/auth/login"
                  variant="emerald"
                  size="lg"
                  className="!px-8 !py-3.5 !text-[15px] sm:!px-4 sm:!py-2 sm:!text-[13px]"
                >
                  Спробувати 7 днів
                </CtaLink>
              </div>

              <div className="mt-auto pt-8 pb-2 sm:mt-12 sm:pt-10 sm:pb-0">
                <p className="text-[11px] font-medium uppercase tracking-[0.14em] text-white/35">
                  Партнери
                </p>
                <div className="mt-4 inline-flex items-center sm:mt-5">
                  {PARTNER_LOGOS.map(({ src, alt }, index) => (
                    <span
                      key={alt}
                      className={cn(
                        "relative inline-flex h-11 w-11 sm:h-14 sm:w-14 shrink-0 overflow-hidden rounded-full bg-white shadow-md ring-2 ring-white/20",
                        index > 0 && "-ml-3.5 sm:-ml-4",
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

                <div className="mt-6 border-t border-white/10 pt-5 sm:mt-7 sm:pt-7">
                  <div className="grid grid-cols-4 gap-1.5 sm:gap-4">
                  {[
                    { value: "100+", label: "джерел" },
                    { value: "1 500+", label: "оголошень" },
                    { value: "< 5 хв", label: "до сповіщення" },
                    { value: "7 днів", label: "безкоштовно" },
                  ].map(({ value, label }) => (
                    <div key={label} className="min-w-0 text-center">
                      <div className="text-[13px] font-semibold leading-none text-white/60 sm:text-xl sm:text-white/80">
                        {value}
                      </div>
                      <div className="mt-1 text-[10px] leading-tight text-white/40 sm:mt-1.5 sm:text-[11px] sm:text-white/45">
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

        <LandingFaq />

        {/* ── VIDEO INSTRUCTIONS ───────────────────────────── */}
        <section className="bg-white section-y">
          <div className="section-wrap">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 lg:gap-12 items-center">
              <div>
                <h2 className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] leading-tight text-ink">
                  Перестань гаяти час на ручний моніторинг
                </h2>
                <div className="mt-5 sm:mt-6 space-y-3">
                  {[
                    "Не витрачаєш годин на пошук по 3+ сайтах",
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
        <section className="bg-white section-y">
          <div className="section-wrap">
            <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-3 mb-8 sm:mb-10">
              <h2 className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] text-ink">Обери план</h2>
              <Link href="/pricing" className="inline-flex items-center gap-1.5 text-[12px] text-muted hover:text-emerald-dark transition-colors group">
                Детальне порівняння
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
                  Знаходь авто швидше за конкурентів
                </h2>
                <p className="mt-2 text-[13px] text-white/50">Без прив&apos;язки карти. Перші 7 днів безкоштовно.</p>
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
