import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PricingPlans } from "@/components/pricing/PricingPlans";
import { CtaLink } from "@/components/ui/CtaLink";
import { cn } from "@/lib/utils";
import { PRICING_COMPARE, PRICING_PLAN_HEADERS } from "@/lib/pricing-plans";
import { IconCheck, IconX } from "@/components/icons";

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
          <PricingPlans variant="page" />

          {/* Compare table */}
          <div className="mb-24 mt-24">
            <h2 className="text-[40px] sm:text-[52px] font-black tracking-tight text-ink mb-3">Повне порівняння</h2>
            <p className="text-[16px] text-muted mb-10 max-w-[480px]">Усі можливості в одній таблиці — обери те, що підходить саме тобі.</p>
            <div className="border border-border/60 rounded-3xl overflow-hidden shadow-card overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="bg-white border-b border-border">
                    <th className="text-left px-6 py-5 text-[13px] font-semibold text-muted w-[40%]">Можливість</th>
                    {PRICING_PLAN_HEADERS.map((h, i) => (
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
                  {PRICING_COMPARE.map(({ feature, free, lite, std, pro }) => (
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
