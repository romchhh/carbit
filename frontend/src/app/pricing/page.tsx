import { Header } from "@/components/layout/Header";
import { Footer } from "@/components/layout/Footer";
import { PricingPlans } from "@/components/pricing/PricingPlans";
import { CtaLink } from "@/components/ui/CtaLink";
import { FaqAccordion } from "@/components/ui/FaqAccordion";
import { cn } from "@/lib/utils";
import { PRICING_COMPARE, PRICING_PLAN_HEADERS } from "@/lib/pricing-plans";
import { IconCheck, IconX } from "@/components/icons";

const PRICING_FAQ = [
  {
    q: "Можна змінити тариф?",
    a: "Так, підвищити або понизити можна будь-коли з кабінету без зупинки сервісу.",
  },
  {
    q: "Є пробний період?",
    a: "Так. Тариф «Безкоштовно» — 7 днів, без прив'язки картки.",
  },
  {
    q: "Звідки беруться оголошення?",
    a: "AUTO.RIA, OLX та тематичні Telegram-канали авторинку.",
  },
  {
    q: "Як оплатити?",
    a: "Карткою Visa/Mastercard через LiqPay або банківським переказом. Деталі — у розділі «Оплата і повернення».",
  },
  {
    q: "Чи є повернення коштів?",
    a: "Так. Умови повернення описані на сторінці /payment.",
  },
  {
    q: "Це фізичний товар?",
    a: "Ні. Carbit — цифрова підписка; доставка не потрібна, доступ надається онлайн.",
  },
] as const;

function Cell({ v }: { v: string | boolean }) {
  if (typeof v === "boolean") {
    return v
      ? <IconCheck size={18} className="text-emerald mx-auto"/>
      : <IconX size={18} className="text-border/80 mx-auto"/>;
  }
  return <span className="text-[13px] text-ink font-semibold sm:text-[14px]">{v}</span>;
}

export default function PricingPage() {
  return (
    <>
      <Header />
      <main className="bg-white min-h-screen">

        {/* Intro — як блок «Обери план» на головній */}
        <section className="border-b border-border/60 pt-[72px] sm:pt-[80px] section-y">
          <div className="section-wrap">
            <h1 className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] text-ink">
              Простий вибір
            </h1>
            <p className="mt-3 max-w-[560px] text-[16px] font-medium leading-relaxed text-ink/70 sm:mt-4 sm:text-[18px]">
              Починай безкоштовно. Плати тільки коли бачиш результат.
            </p>
          </div>
        </section>

        {/* Тарифи — ті самі картки, що на головній */}
        <section className="section-y">
          <div className="section-wrap">
            <PricingPlans variant="home" />
          </div>
        </section>

        {/* Порівняння */}
        <section className="section-y border-t border-border/60">
          <div className="section-wrap">
            <h2 className="text-[28px] sm:text-[36px] font-semibold tracking-[-0.02em] text-ink">
              Повне порівняння
            </h2>
            <p className="mt-3 max-w-[480px] text-[16px] leading-relaxed text-ink/70 sm:mt-4 sm:text-[18px]">
              Усі можливості в одній таблиці — обери те, що підходить саме тобі.
            </p>
            <div className="mt-8 sm:mt-10 border border-border/60 rounded-2xl sm:rounded-3xl overflow-hidden shadow-card overflow-x-auto">
              <table className="w-full min-w-[640px]">
                <thead>
                  <tr className="bg-white border-b border-border">
                    <th className="text-left px-5 py-4 text-[12px] font-semibold text-muted w-[40%] sm:px-6 sm:py-5 sm:text-[13px]">Можливість</th>
                    {PRICING_PLAN_HEADERS.map((h, i) => (
                      <th
                        key={h}
                        className={cn(
                          "px-3 py-4 text-[12px] font-bold text-center sm:px-4 sm:py-5 sm:text-[13px]",
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
                      <td className="px-5 py-3.5 text-[13px] font-medium text-ink sm:px-6 sm:py-4 sm:text-[14px]">{feature}</td>
                      {[free, lite, std, pro].map((v, j) => (
                        <td
                          key={j}
                          className={cn("px-3 py-3.5 text-center sm:px-4 sm:py-4", j === 2 && "bg-emerald/[0.06]")}
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
        </section>

        {/* FAQ */}
        <section className="section-y border-t border-border/60 bg-surface/30">
          <div className="section-wrap">
            <h2 className="mb-8 text-[28px] font-semibold tracking-[-0.02em] text-ink sm:mb-10 sm:text-[36px]">
              Часті питання
            </h2>
            <FaqAccordion items={PRICING_FAQ} />
          </div>
        </section>

        {/* CTA — як на головній */}
        <section className="section-y">
          <div className="section-wrap">
            <div className="relative bg-ink rounded-2xl sm:rounded-3xl px-6 sm:px-10 py-8 sm:py-10 overflow-hidden flex flex-col lg:flex-row items-center justify-between gap-6">
              <div className="absolute top-0 right-0 w-64 h-64 bg-emerald/15 rounded-full blur-[100px] pointer-events-none" />
              <div className="relative max-w-[480px] text-center lg:text-left">
                <h2 className="text-[26px] sm:text-[32px] font-semibold text-white tracking-[-0.02em] leading-tight">
                  Починай безкоштовно сьогодні
                </h2>
                <p className="mt-2 text-[13px] text-white/50">Без прив&apos;язки карти. Перші 7 днів безкоштовно.</p>
              </div>
              <CtaLink href="/auth/login" variant="emerald" size="lg" className="relative shrink-0">
                Спробувати
              </CtaLink>
            </div>
          </div>
        </section>
      </main>
      <Footer />
    </>
  );
}
