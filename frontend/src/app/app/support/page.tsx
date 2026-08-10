"use client";

import { AppPage, AppSection } from "@/components/layout/AppPage";
import { IconTelegram } from "@/components/icons";
import { FaqAccordion } from "@/components/ui/FaqAccordion";
import { SocialIconRow } from "@/components/social/SocialIconRow";
import { CARBIT_FAQ_ITEMS } from "@/lib/faq-items";
import { getTelegramSupportBotMention, getTelegramSupportBotUrl } from "@/lib/telegram";

export default function SupportPage() {
  return (
    <AppPage
      title="Підтримка"
      description="Часті питання про пошук, тарифи та оплату. Якщо відповіді немає — напишіть боту."
    >
      <AppSection>
        <a
          href={getTelegramSupportBotUrl()}
          target="_blank"
          rel="noopener noreferrer"
          className="mb-6 flex items-center justify-between gap-3 rounded-2xl border border-[#229ED9]/25 bg-[#E8F4FD]/60 px-4 py-4 transition-colors hover:bg-[#E8F4FD] sm:px-5"
        >
          <div className="flex min-w-0 items-center gap-3">
            <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-white">
              <IconTelegram size={18} className="text-[#229ED9]" />
            </span>
            <div className="min-w-0">
              <div className="text-[14px] font-semibold text-ink">Написати в Telegram</div>
              <div className="mt-0.5 text-[12px] text-muted">
                {getTelegramSupportBotMention()} · тариф, оплата, сервіс
              </div>
            </div>
          </div>
          <span className="shrink-0 text-[12px] font-semibold text-[#229ED9]">Відкрити</span>
        </a>

        <h2 className="mb-4 text-[15px] font-semibold text-ink">Часті питання</h2>
        <FaqAccordion items={CARBIT_FAQ_ITEMS} className="max-w-none" />

        <div className="mt-8 border-t border-border/60 pt-5">
          <p className="mb-3 text-center text-[12px] text-muted">Ми в соцмережах</p>
          <SocialIconRow size="md" />
        </div>
      </AppSection>
    </AppPage>
  );
}
