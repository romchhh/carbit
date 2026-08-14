import { FaqAccordion } from "@/components/ui/FaqAccordion";
import { CARBIT_FAQ_ITEMS } from "@/lib/faq-items";

export function LandingFaq() {
  return (
    <section id="faq" className="section-y bg-surface/30">
      <div className="section-wrap">
        <div className="mb-8 flex flex-col gap-3 sm:mb-10 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="text-[28px] font-semibold tracking-[-0.02em] text-ink sm:text-[36px]">
            Часті питання про пошук авто
          </h2>
          <p className="max-w-[320px] text-[14px] leading-relaxed text-muted sm:text-[15px]">
            Джерела оголошень, сповіщення та підписка на моніторинг
          </p>
        </div>

        <FaqAccordion items={CARBIT_FAQ_ITEMS} columns={2} />
      </div>
    </section>
  );
}
