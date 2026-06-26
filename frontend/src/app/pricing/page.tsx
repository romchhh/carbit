import Link from "next/link";
import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { CtaLink } from "@/components/ui/CtaLink";
import { cn } from "@/lib/utils";
import { IconCheck, IconX } from "@/components/icons";

const plans = [
  {
    name: "Безкоштовно", price: "0", period: "7 днів тест-драйв",
    features: ["1 пошуковий запит", "Оновлення раз на годину", "Вебкабінет"],
    missing: ["Telegram-бот", "Анти-дубль", "Оцінка ризиків", "Пріоритет"],
    cta: "Почати безкоштовно", href: "/auth/login", accent: false, popular: false,
  },
  {
    name: "Lite", price: "500", period: "грн / місяць",
    features: ["3 пошукових запити", "Оновлення кожні 30 хв", "Telegram-бот", "Анти-дубль"],
    missing: ["Оцінка ризиків", "Пріоритетна підтримка"],
    cta: "Вибрати Lite", href: "/auth/login?plan=lite", accent: false, popular: false,
  },
  {
    name: "Стандарт", price: "2 000", period: "грн / місяць",
    features: ["10 пошукових запитів", "Оновлення кожні 5 хв", "Telegram-бот", "Анти-дубль", "Оцінка ризиків", "Експорт Excel"],
    missing: [],
    cta: "Вибрати Стандарт", href: "/auth/login?plan=standard", accent: true, popular: true,
  },
  {
    name: "Pro", price: "6 000", period: "грн / місяць",
    features: ["50 запитів", "Оновлення в реальному часі", "Telegram-бот", "Анти-дубль", "Оцінка ризиків", "Повний API-доступ", "Персональний менеджер", "Підтримка 24/7"],
    missing: [],
    cta: "Зв'язатися", href: "/contact", accent: false, popular: false,
  },
];

const compare = [
  { feature: "Пошукові запити", free: "1", lite: "3", std: "10", pro: "50" },
  { feature: "Частота оновлення", free: "1 год", lite: "30 хв", std: "5 хв", pro: "Реал-тайм" },
  { feature: "Telegram-бот", free: false, lite: true, std: true, pro: true },
  { feature: "Анти-дубль", free: false, lite: true, std: true, pro: true },
  { feature: "Оцінка ризиків", free: false, lite: false, std: true, pro: true },
  { feature: "Експорт Excel/CSV", free: false, lite: false, std: true, pro: true },
  { feature: "API-доступ", free: false, lite: false, std: false, pro: true },
  { feature: "Персональний менеджер", free: false, lite: false, std: false, pro: true },
];

const planHeaders = ["Безкоштовно", "Lite", "Стандарт", "Pro"] as const;

function Cell({ v }: { v: string | boolean }) {
  if (typeof v === "boolean") {
    return v
      ? <IconCheck size={18} className="text-emerald mx-auto"/>
      : <IconX size={18} className="text-border/80 mx-auto"/>;
  }
  return <span className="text-[14px] text-ink font-semibold">{v}</span>;
}

export default function PricingPage() {
  return (
    <>
      <Header />
      <main className="bg-white min-h-screen">
        {/* Hero */}
        <section className="border-b border-border/60">
          <div className="max-w-[1280px] mx-auto px-8 pt-28 pb-20 text-center">
            <h1 className="text-[52px] sm:text-[64px] lg:text-[72px] font-black tracking-[-0.03em] text-ink leading-[0.95]">
              Простий вибір
            </h1>
            <p className="mt-6 text-[18px] sm:text-[20px] text-muted leading-relaxed max-w-[520px] mx-auto">
              Починай безкоштовно. Плати тільки коли бачиш результат.
            </p>
          </div>
        </section>

        <div className="max-w-[1280px] mx-auto px-8 py-20">
          {/* Plan cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-6 mb-24">
            {plans.map(({ name, price, period, features, missing, cta, href, accent, popular }) => (
              <div
                key={name}
                className={cn(
                  "relative rounded-3xl p-8 flex flex-col transition-all duration-300 hover:-translate-y-1",
                  accent
                    ? "bg-ink text-white shadow-xl shadow-ink/25 ring-2 ring-emerald/50 xl:scale-[1.03] xl:-mt-2 xl:mb-2"
                    : "card-rounded"
                )}
              >
                {popular && (
                  <span className="absolute -top-3.5 left-1/2 -translate-x-1/2 bg-emerald text-white text-[11px] font-bold uppercase tracking-wider px-4 py-1.5 rounded-full shadow-lg shadow-emerald/30">
                    Популярний
                  </span>
                )}
                <h3 className={cn("text-[22px] font-bold", accent ? "text-white" : "text-ink")}>{name}</h3>
                <div className="mt-5 flex items-end gap-1.5">
                  <span className={cn("text-[52px] font-black leading-none tracking-tight", accent ? "text-emerald" : "text-ink")}>
                    {price}
                  </span>
                  {price !== "0" && (
                    <span className={cn("pb-2 text-[15px] font-medium", accent ? "text-white/40" : "text-muted")}>грн</span>
                  )}
                </div>
                <p className={cn("text-[14px] mt-1 mb-8", accent ? "text-white/45" : "text-muted")}>{period}</p>
                <Link
                  href={href}
                  className={cn(
                    "group flex items-center justify-center gap-2 text-[15px] font-semibold py-3.5 rounded-full transition-all duration-300 mb-8 hover:-translate-y-0.5",
                    accent
                      ? "bg-emerald text-white hover:bg-emerald-dark shadow-lg shadow-emerald/30"
                      : "border border-border text-ink hover:bg-emerald hover:text-white hover:border-emerald"
                  )}
                >
                  {cta}
                  <span className={cn(
                    "w-7 h-7 rounded-full flex items-center justify-center text-[13px] group-hover:translate-x-0.5 transition-transform",
                    accent ? "bg-white/20" : "bg-ink/5 group-hover:bg-white/20"
                  )}>→</span>
                </Link>
                <div className="space-y-3.5 flex-1">
                  {features.map(f => (
                    <div key={f} className={cn("flex gap-3 text-[14px]", accent ? "text-white/80" : "text-ink")}>
                      <IconCheck size={16} className="text-emerald shrink-0 mt-0.5"/>
                      {f}
                    </div>
                  ))}
                  {missing.map(f => (
                    <div key={f} className="flex gap-3 text-[14px] text-muted/50">
                      <IconX size={16} className="shrink-0 mt-0.5"/>
                      {f}
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {/* Compare table */}
          <div className="mb-24">
            <h2 className="text-[40px] sm:text-[52px] font-black tracking-tight text-ink mb-3">Повне порівняння</h2>
            <p className="text-[16px] text-muted mb-10 max-w-[480px]">Усі можливості в одній таблиці — обери те, що підходить саме тобі.</p>
            <div className="border border-border/60 rounded-3xl overflow-hidden shadow-card overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="bg-white border-b border-border">
                    <th className="text-left px-6 py-5 text-[13px] font-semibold text-muted w-[40%]">Можливість</th>
                    {planHeaders.map((h, i) => (
                      <th
                        key={h}
                        className={cn(
                          "px-4 py-5 text-[13px] font-bold text-center",
                          i === 2 ? "bg-emerald/10 text-emerald-dark" : "text-ink"
                        )}
                      >
                        {h}
                        {i === 2 && <span className="block text-[10px] font-semibold text-emerald mt-0.5 uppercase tracking-wide">рекомендуємо</span>}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {compare.map(({ feature, free, lite, std, pro }) => (
                    <tr key={feature} className="border-t border-border/50 hover:bg-surface/30 transition-colors">
                      <td className="px-6 py-4 text-[14px] font-medium text-ink">{feature}</td>
                      {[free, lite, std, pro].map((v, j) => (
                        <td
                          key={j}
                          className={cn("px-4 py-4 text-center", j === 2 && "bg-emerald/[0.06]")}
                        >
                          <Cell v={v as string | boolean}/>
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* FAQ */}
          <div className="mb-24">
            <h2 className="text-[40px] sm:text-[52px] font-black tracking-tight text-ink mb-10">Часті питання</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {[
                ["Можна змінити тариф?", "Так, підвищити або понизити можна будь-коли з кабінету без зупинки сервісу."],
                ["Є пробний період?", "7 днів на Стандарт-тарифі — безкоштовно, без прив'язки карти."],
                ["Звідки беруться оголошення?", "AUTO.RIA API, OLX API та парсинг тематичних Telegram-каналів авторинку."],
                ["Як оплатити?", "Карткою Visa/MC, через LiqPay або Monobank. Для юросіб — за договором."],
              ].map(([q, a]) => (
                <div key={q} className="card-rounded p-8 hover:border-emerald/20">
                  <h4 className="text-[18px] font-bold text-ink">{q}</h4>
                  <p className="mt-3 text-[15px] text-muted leading-relaxed">{a}</p>
                </div>
              ))}
            </div>
          </div>

          {/* CTA */}
          <div className="relative bg-ink rounded-[2.5rem] px-10 sm:px-16 py-14 flex flex-col lg:flex-row items-center justify-between gap-10 overflow-hidden">
            <div className="absolute top-0 right-0 w-80 h-80 bg-emerald/15 rounded-full blur-[100px] pointer-events-none" />
            <div className="relative text-center lg:text-left max-w-[520px]">
              <h2 className="text-[36px] sm:text-[44px] font-black text-white tracking-tight leading-tight">
                Починай безкоштовно сьогодні
              </h2>
              <p className="mt-4 text-[17px] text-white/45">Без прив&apos;язки карти. 7 днів повного доступу.</p>
            </div>
            <CtaLink href="/auth/login" variant="emerald" size="lg" className="relative shrink-0">
              Спробувати
            </CtaLink>
          </div>
        </div>
      </main>
      <Footer />
    </>
  );
}
