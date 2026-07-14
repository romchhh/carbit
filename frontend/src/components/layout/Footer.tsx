import Link from "next/link";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";
import { SUPPORT_EMAIL } from "@/lib/pricing-plans";

const columns = [
  {
    title: "Продукт",
    links: [
      { label: "Пошук", href: "/app/search" },
      { label: "Тарифи", href: "/pricing" },
      { label: "Оплата і повернення", href: "/payment" },
    ],
  },
  {
    title: "Документи",
    links: [
      { label: "Умови використання", href: "/terms" },
      { label: "Конфіденційність", href: "/privacy" },
      { label: "Оплата і повернення", href: "/payment" },
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
      <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-10 sm:py-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8 text-center sm:text-left">
        <div className="flex flex-col items-center sm:items-start">
          <Link href="/" className="flex items-center w-fit group">
            <CarbitLogo variant="full" height={36} light className="transition-opacity group-hover:opacity-90" />
          </Link>
          <p className="mt-3 text-[12px] text-white/50 leading-snug max-w-[280px] sm:max-w-none">
            Агрегатор оголошень авторинку України для перекупників та підбірників.
          </p>
          <p className="mt-3 text-[11px] text-white/40 leading-snug max-w-[280px] sm:max-w-none">
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
            <div className="text-[11px] font-semibold tracking-[0.1em] uppercase text-white/40 mb-3">{title}</div>
            <ul className="space-y-2">
              {links.map(({ label, href }) => (
                <li key={label}>
                  <Link href={href} className="text-[12px] text-white/65 hover:text-emerald transition-colors">
                    {label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10">
        <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-4 flex flex-col sm:flex-row justify-between items-center gap-2">
          <span className="text-[12px] text-white/40">© 2026 Carbit</span>
          <div className="flex flex-wrap justify-center gap-4 text-[12px] text-white/40">
            <Link href="/payment" className="hover:text-white transition-colors">
              Оплата і повернення
            </Link>
            <Link href="/terms" className="hover:text-white transition-colors">
              Умови використання
            </Link>
            <Link href="/privacy" className="hover:text-white transition-colors">
              Політика конфіденційності
            </Link>
          </div>
        </div>
      </div>
    </footer>
  );
}
