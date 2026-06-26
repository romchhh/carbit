import Image from "next/image";
import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { FreshListingsCarousel } from "@/components/listings/FreshListingsCarousel";
import { CtaLink } from "@/components/ui/CtaLink";
import { cn } from "@/lib/utils";
import { IconCheck, IconX, IconArrowDown, IconSearch, IconBell, IconShield, IconTelegram, IconGlobe, IconZap } from "@/components/icons";

const HERO_IMAGE = "https://images.unsplash.com/photo-1503376780353-7e6692767b70?auto=format&fit=crop&w=1920&q=80";

export default function HomePage() {
  return (
    <>
      <Header />
      <main className="bg-white">

        {/* ── HERO ─────────────────────────────────────────── */}
        <section className="relative min-h-[100dvh] flex items-center overflow-hidden pt-[64px] sm:pt-[72px]">
          <Image
            src={HERO_IMAGE}
            alt=""
            fill
            priority
            className="object-cover object-center scale-105"
            sizes="100vw"
          />
          <div className="absolute inset-0 bg-gradient-to-br from-ink/95 via-ink/80 to-ink/50" />
          <div className="absolute inset-0 bg-gradient-to-t from-ink/60 via-transparent to-transparent" />

          <div className="absolute top-1/4 right-[15%] w-48 h-48 sm:w-72 sm:h-72 bg-emerald/20 rounded-full blur-[100px] pointer-events-none animate-float" />
          <div className="absolute bottom-1/4 left-[10%] w-32 h-32 sm:w-48 sm:h-48 bg-emerald/10 rounded-full blur-[80px] pointer-events-none" />

          <div className="relative section-wrap py-12 sm:py-16 w-full">
            <div className="max-w-[620px]">
              <h1 className="text-[36px] sm:text-[52px] lg:text-[60px] font-semibold leading-[1.05] tracking-[-0.02em] text-white animate-fade-up">
                Знайди авто раніше{" "}
                <span className="text-emerald">конкурентів</span>
              </h1>

              <p className="mt-4 sm:mt-5 text-[14px] sm:text-[16px] text-white leading-snug max-w-[480px] animate-fade-up-delay">
                AUTO.RIA, OLX і Telegram в одному пошуку — анти-дубль і сигнал «брати / торгуватись».
              </p>

              <div className="mt-6 sm:mt-8 flex flex-wrap items-center gap-3 sm:gap-4 animate-fade-up-delay">
                <CtaLink href="/auth/login" variant="emerald" size="lg">
                  Спробувати 7 днів
                </CtaLink>
                <Link href="#how-it-works" className="text-link group">
                  Як це працює
                  <span className="text-link-arrow">
                    <IconArrowDown size={12} />
                  </span>
                </Link>
              </div>

              <div className="mt-8 sm:mt-10 grid grid-cols-2 lg:grid-cols-4 gap-2.5 sm:gap-3 pt-6 sm:pt-8 border-t border-white/10">
                {[
                  { value: "3", label: "джерела" },
                  { value: "1 200+", label: "оголошень/день" },
                  { value: "< 5 хв", label: "до сповіщення" },
                  { value: "72%", label: "готові платити" },
                ].map(({ value, label }) => (
                  <div key={label} className="stat-pill">
                    <div className="text-xl sm:text-2xl font-semibold text-white tracking-tight leading-none">{value}</div>
                    <div className="text-[10px] sm:text-[11px] text-white/50 mt-1.5 uppercase tracking-wider font-medium leading-snug">{label}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        <FreshListingsCarousel />

        {/* ── HOW IT WORKS ─────────────────────────────────── */}
        <section id="how-it-works" className="bg-white section-y">
          <div className="section-wrap">
            <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 mb-8 sm:mb-10">
              <h2 className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] text-ink leading-tight">
                Три кроки до угоди
              </h2>
              <p className="text-muted text-[13px] sm:text-[14px] max-w-[300px] leading-snug">
                Від реєстрації до першого сповіщення — менше 10 хвилин
              </p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-5">
              {[
                { n: "01", icon: <IconSearch size={36}/>, title: "Налаштуй пошук", desc: "Марка, модель, рік, ціна, регіон. До 10 запитів одночасно." },
                { n: "02", icon: <IconGlobe size={36}/>, title: "Сканування скрізь", desc: "AUTO.RIA, OLX і Telegram. Анти-дубль злипає однакові авто." },
                { n: "03", icon: <IconBell size={36}/>, title: "Сповіщення миттєво", desc: "Нове авто в Telegram за 5 хвилин з оцінкою ризику." },
              ].map(({ n, icon, title, desc }) => (
                <article key={n} className="card-rounded p-5 sm:p-6 group">
                  <div className="flex items-start justify-between gap-3">
                    <span className="text-[40px] sm:text-[48px] font-semibold leading-none tracking-tighter text-emerald/25 group-hover:text-emerald/40 transition-colors duration-300">
                      {n}
                    </span>
                    <span className="text-emerald shrink-0 transition-transform duration-300 group-hover:scale-110">
                      {icon}
                    </span>
                  </div>
                  <h3 className="mt-4 text-[18px] sm:text-[20px] font-semibold tracking-tight text-ink">{title}</h3>
                  <p className="mt-2 text-[13px] text-muted leading-snug">{desc}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        {/* ── PAIN / VALUE PROP ────────────────────────────── */}
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

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
                {[
                  { icon: <IconShield size={28}/>, title: "Анти-хлам", desc: "Оцінка ризиків по пробігу, власниках, джерелу" },
                  { icon: <IconTelegram size={28}/>, title: "Telegram-бот", desc: "Сповіщення прямо в месенджер без зайвих кліків" },
                  { icon: <IconSearch size={28}/>, title: "Анти-дубль", desc: "AUTO.RIA + OLX = одне оголошення, не два" },
                  { icon: <IconZap size={28}/>, title: "5 хвилин", desc: "Нові авто у чаті через 5 хвилин після появи" },
                ].map(({ icon, title, desc }) => (
                  <div key={title} className="card-rounded p-5 group">
                    <span className="text-emerald inline-block transition-transform duration-300 group-hover:scale-110">
                      {icon}
                    </span>
                    <h4 className="mt-3 text-[16px] font-semibold text-ink">{title}</h4>
                    <p className="mt-1.5 text-[12px] text-muted leading-snug">{desc}</p>
                  </div>
                ))}
              </div>
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

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-5">
              {[
                {
                  name: "Безкоштовно", price: "0", period: "7 днів", sub: "тест-драйв",
                  features: ["1 пошуковий запит","Оновлення раз на годину","Кабінет"],
                  missing: ["Telegram-бот","Анти-дубль","Оцінка ризиків"],
                  cta: "Почати", href: "/auth/login", accent: false,
                },
                {
                  name: "Lite", price: "500", period: "грн/міс", sub: "для себе",
                  features: ["3 запити","Оновлення кожні 30 хв","Telegram-бот","Анти-дубль"],
                  missing: ["Оцінка ризиків","Пріоритет"],
                  cta: "Вибрати Lite", href: "/auth/login?plan=lite", accent: false,
                },
                {
                  name: "Стандарт", price: "2 000", period: "грн/міс", sub: "для перекупників",
                  features: ["10 запитів","Оновлення кожні 5 хв","Telegram-бот","Анти-дубль","Оцінка ризиків","Експорт Excel"],
                  missing: [],
                  cta: "Вибрати Стандарт", href: "/auth/login?plan=standard", accent: true,
                },
              ].map(({ name, price, period, features, missing, cta, href, accent }) => (
                <article key={name} className={cn(
                  "rounded-2xl p-5 sm:p-6 transition-all duration-300 hover:-translate-y-0.5",
                  accent
                    ? "bg-ink text-white shadow-xl shadow-ink/30 ring-2 ring-emerald/50 md:scale-[1.02]"
                    : "card-rounded"
                )}>
                  <h3 className={cn("text-[20px] font-semibold", accent ? "text-white" : "text-ink")}>{name}</h3>
                  <div className="mt-3 flex items-end gap-1.5">
                    <span className={cn("text-[32px] sm:text-[36px] font-semibold leading-none tracking-tight", accent ? "text-emerald" : "text-ink")}>{price}</span>
                    <span className={cn("pb-1 text-[12px]", accent ? "text-white/40" : "text-muted")}>{period}</span>
                  </div>
                  <Link href={href}
                    className={cn(
                      "mt-5 group flex items-center justify-center gap-1.5 text-center text-[12px] font-medium py-2 rounded-full transition-all duration-300 hover:-translate-y-0.5",
                      accent
                        ? "bg-emerald text-white hover:bg-emerald-dark shadow-lg shadow-emerald/30"
                        : "bg-surface border border-border text-ink hover:bg-emerald hover:text-white hover:border-emerald"
                    )}>
                    {cta}
                    <span className={cn(
                      "w-5 h-5 rounded-full flex items-center justify-center transition-all group-hover:translate-x-0.5 text-[10px]",
                      accent ? "bg-white/20" : "bg-ink/5 group-hover:bg-white/20"
                    )}>→</span>
                  </Link>
                  <div className="mt-5 space-y-2.5">
                    {features.map(f => (
                      <div key={f} className={cn("flex gap-2 text-[12px]", accent ? "text-white/80" : "text-ink")}>
                        <IconCheck size={14} className="text-emerald shrink-0 mt-0.5"/>
                        {f}
                      </div>
                    ))}
                    {missing.map(f => (
                      <div key={f} className="flex gap-2 text-[12px] text-muted opacity-50">
                        <IconX size={14} className="shrink-0 mt-0.5"/>
                        {f}
                      </div>
                    ))}
                  </div>
                </article>
              ))}
            </div>
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
