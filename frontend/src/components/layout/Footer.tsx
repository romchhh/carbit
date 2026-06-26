import Link from "next/link";
import { LogoIcon } from "@/components/brand/LogoIcon";

const columns = [
  { title: "Продукт", links: [{ label: "Пошук", href: "/app/search" }, { label: "Тарифи", href: "/pricing" }, { label: "API", href: "#" }] },
  { title: "Компанія", links: [{ label: "Про нас", href: "#" }, { label: "Блог", href: "#" }, { label: "Контакти", href: "#" }] },
  { title: "Підтримка", links: [{ label: "Довідка", href: "#" }, { label: "Документація", href: "#" }, { label: "Статус", href: "#" }] },
];

export function Footer() {
  return (
    <footer className="bg-ink text-white">
      <div className="max-w-[1280px] mx-auto px-5 sm:px-6 py-10 sm:py-12 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 sm:gap-8 text-center sm:text-left">
        <div className="flex flex-col items-center sm:items-start">
          <Link href="/" className="flex items-center gap-2.5 w-fit group">
            <span className="w-10 h-10 rounded-full bg-white/10 ring-1 ring-white/20 flex items-center justify-center">
              <LogoIcon size={18} light />
            </span>
            <span className="text-[15px] font-semibold tracking-tight text-white group-hover:text-emerald transition-colors">Carbit</span>
          </Link>
          <p className="mt-3 text-[12px] text-white/50 leading-snug max-w-[280px] sm:max-w-none">
            Агрегатор оголошень авторинку України для перекупників та підбірників.
          </p>
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
          <div className="flex gap-4 text-[12px] text-white/40">
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
