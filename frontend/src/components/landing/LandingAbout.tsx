/**
 * Короткий SEO-блок: що таке Carbit і під які запити (пошук авто / моніторинг).
 * Один блок — одна думка, без карток і зайвого UI.
 */
export function LandingAbout() {
  return (
    <section id="about" className="section-y border-t border-border/50 bg-surface/30" aria-labelledby="about-heading">
      <div className="section-wrap max-w-[720px]">
        <h2
          id="about-heading"
          className="text-[28px] font-semibold tracking-[-0.02em] text-ink sm:text-[36px]"
        >
          Агрегатор пошуку авто в Україні
        </h2>
        <div className="mt-5 space-y-4 text-[15px] leading-relaxed text-ink/75 sm:mt-6 sm:text-[16px]">
          <p>
            <strong className="font-semibold text-ink">Carbit</strong> — сервіс для тих, хто шукає
            авто з пробігом і хоче бачити свіжі оголошення раніше за ринок. Ми збираємо пропозиції з{" "}
            <strong className="font-semibold text-ink">AUTO.RIA</strong>,{" "}
            <strong className="font-semibold text-ink">OLX</strong>, Імперія Авто, uDrive і тематичних{" "}
            <strong className="font-semibold text-ink">Telegram</strong>-каналів в одному пошуку.
          </p>
          <p>
            Налаштуйте фільтри за маркою, моделлю, ціною й регіоном — далі працює моніторинг
            оголошень: нові авто приходять у кабінет і в Telegram, зазвичай протягом кількох хвилин.
            Дублікати з різних майданчиків зливаємо в одне авто, щоб не витрачати час на повторні
            картки.
          </p>
          <p>
            Підходить перекупникам, підбірникам і приватним покупцям, яким важливі швидкість і повна
            картина ринку, а не ручний перегляд десятків вкладок щодня.
          </p>
        </div>
      </div>
    </section>
  );
}
