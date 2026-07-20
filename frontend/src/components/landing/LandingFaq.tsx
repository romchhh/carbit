const FAQ_ITEMS = [
  {
    q: "Звідки беруться оголошення?",
    a: "AUTO.RIA, OLX та тематичні Telegram-канали авторинку. Дублікати зливаємо в одне авто.",
  },
  {
    q: "Як швидко приходять сповіщення?",
    a: "Зазвичай до 5 хвилин після появи оголошення. Нові авто — у Telegram і в кабінеті.",
  },
  {
    q: "Скільки моніторингів можна тримати?",
    a: "Залежить від тарифу: від 1 на безкоштовному до 100 на Бізнесі. Ліміт видно в кабінеті.",
  },
  {
    q: "Є пробний період?",
    a: "Так. Тариф «Безкоштовно» — 7 днів, без прив’язки картки.",
  },
  {
    q: "Як оплатити підписку?",
    a: "Карткою Visa/Mastercard через LiqPay у розділі «Підписка». Деталі — на сторінці оплати.",
  },
  {
    q: "Можна змінити або скасувати тариф?",
    a: "Так. Підвищити, понизити або вимкнути автопродовження можна будь-коли з кабінету.",
  },
] as const;

export function LandingFaq() {
  return (
    <section id="faq" className="bg-white section-y">
      <div className="section-wrap">
        <div className="mb-8 flex flex-col gap-3 sm:mb-10 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="text-[28px] font-semibold tracking-[-0.02em] text-ink sm:text-[36px]">
            Часті питання
          </h2>
          <p className="max-w-[320px] text-[14px] leading-relaxed text-muted sm:text-[15px]">
            Коротко про пошук, сповіщення та підписку
          </p>
        </div>

        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 sm:gap-5">
          {FAQ_ITEMS.map(({ q, a }) => (
            <div
              key={q}
              className="rounded-2xl border border-border/70 bg-white p-6 transition-colors hover:border-emerald/25 sm:p-7"
            >
              <h3 className="text-[16px] font-semibold text-ink sm:text-[17px]">{q}</h3>
              <p className="mt-2.5 text-[14px] leading-relaxed text-muted">{a}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
