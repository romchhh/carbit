import Link from "next/link";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";
import { SocialIconRow } from "@/components/social/SocialIconRow";
import { INSTAGRAM_HANDLE, INSTAGRAM_URL, TIKTOK_HANDLE, TIKTOK_URL } from "@/lib/social-links";
import { SUPPORT_EMAIL } from "@/lib/pricing-plans";

const columns: {
  title: string;
  links: { label: string; href: string; external?: boolean }[];
}[] = [
  {
    title: "Продукт",
    links: [
      { label: "Пошук авто", href: "/#search" },
      { label: "Як працює", href: "/#how-it-works" },
      { label: "Тарифи", href: "/pricing" },
      { label: "Оплата і повернення", href: "/payment" },
    ],
  },
  {
    title: "Документи",
    links: [
      { label: "Публічна оферта", href: "/oferta" },
      { label: "Умови використання", href: "/terms" },
      { label: "Конфіденційність", href: "/privacy" },
    ],
  },
  {
    title: "Підтримка",
    links: [{ label: SUPPORT_EMAIL, href: `mailto:${SUPPORT_EMAIL}` }],
  },
];

export function Footer() {
  return (
    <footer className="bg-ink text-white">
      <div className="mx-auto grid max-w-[1280px] grid-cols-1 gap-6 px-5 py-10 text-center sm:grid-cols-2 sm:gap-8 sm:px-6 sm:py-12 sm:text-left lg:grid-cols-5">
        <div className="flex flex-col items-center sm:items-start">
          <Link href="/" className="group flex w-fit items-center">
            <CarbitLogo variant="full" height={36} light className="transition-opacity group-hover:opacity-90" />
          </Link>
          <p className="mt-3 max-w-[280px] text-[12px] leading-snug text-white/50 sm:max-w-none">
            Пошук і моніторинг авто оголошень з AUTO.RIA, OLX і Telegram для перекупників та
            підбірників.
          </p>
          <p className="mt-3 max-w-[280px] text-[11px] leading-snug text-white/40 sm:max-w-none">
            ФОП Білоус О. В.
            <br />
            02055, м. Київ, вул. Урлівська, 20, кв. 79
          </p>
          <div className="mt-4 flex flex-col items-center gap-2 sm:items-start">
            <span className="text-[10px] uppercase tracking-wider text-white/35">Оплата через</span>
            <a
              href="https://www.liqpay.ua"
              target="_blank"
              rel="noopener noreferrer"
              aria-label="LiqPay"
              className="opacity-90 transition-opacity hover:opacity-100"
            >
              <LiqPayLogo variant="white" height={22} />
            </a>
          </div>
        </div>
        {columns.map(({ title, links }) => (
          <div key={title} className="flex flex-col items-center sm:items-start">
            <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-white/40">
              {title}
            </div>
            <ul className="space-y-2">
              {links.map(({ label, href, external }) => (
                <li key={label}>
                  {external ? (
                    <a
                      href={href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-[12px] text-white/65 transition-colors hover:text-emerald"
                    >
                      {label}
                    </a>
                  ) : (
                    <Link href={href} className="text-[12px] text-white/65 transition-colors hover:text-emerald">
                      {label}
                    </Link>
                  )}
                </li>
              ))}
            </ul>
          </div>
        ))}
        <div className="flex flex-col items-center sm:items-start">
          <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.1em] text-white/40">
            Соцмережі
          </div>
          <SocialIconRow variant="light" className="justify-center sm:justify-start" />
          <ul className="mt-3 space-y-2">
            <li>
              <a
                href={INSTAGRAM_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[12px] text-white/65 transition-colors hover:text-emerald"
              >
                Instagram @{INSTAGRAM_HANDLE}
              </a>
            </li>
            <li>
              <a
                href={TIKTOK_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-[12px] text-white/65 transition-colors hover:text-emerald"
              >
                TikTok @{TIKTOK_HANDLE}
              </a>
            </li>
          </ul>
        </div>
      </div>
      <div className="border-t border-white/10">
        <div className="mx-auto flex max-w-[1280px] flex-col items-center justify-between gap-2 px-5 py-4 sm:flex-row sm:px-6">
          <span className="text-[12px] text-white/40">© 2026 Carbit</span>
          <div className="flex flex-wrap justify-center gap-4 text-[12px] text-white/40">
            <Link href="/oferta" className="transition-colors hover:text-white">
              Публічна оферта
            </Link>
            <Link href="/payment" className="transition-colors hover:text-white">
              Оплата і повернення
            </Link>
            <Link href="/terms" className="transition-colors hover:text-white">
              Умови використання
            </Link>
            <Link href="/privacy" className="transition-colors hover:text-white">
              Політика конфіденційності
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
