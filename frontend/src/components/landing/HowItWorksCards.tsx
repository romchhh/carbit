import Image from "next/image";
import { CtaLink } from "@/components/ui/CtaLink";
import { LANDING_IMAGES } from "@/lib/brand-assets";

const STEPS = [
  {
    title: "Налаштуй пошук",
    description: "Марка, модель, рік, ціна, регіон. До 10 запитів одночасно.",
    cta: "Створити запит",
    href: "/auth/login",
    image: LANDING_IMAGES.howItWorksSetup,
  },
  {
    title: "Сканування скрізь",
    description: "AUTO.RIA, OLX і Telegram. Анти-дубль злипає однакові авто.",
    cta: "Спробувати",
    href: "/auth/login",
    image: LANDING_IMAGES.howItWorksScan,
  },
  {
    title: "Сповіщення миттєво",
    description: "Нове авто в Telegram за 5 хвилин з оцінкою ризику.",
    cta: "Підключити Telegram",
    href: "/auth/login",
    image: LANDING_IMAGES.howItWorksNotify,
  },
] as const;

export function HowItWorksCards() {
  return (
    <section id="how-it-works" className="bg-white section-y">
      <div className="section-wrap">
        <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-4 mb-10 sm:mb-12">
          <h2 className="text-[32px] sm:text-[40px] font-bold tracking-[-0.03em] text-ink leading-tight">
            Три кроки до угоди
          </h2>
          <p className="text-ink/70 text-[16px] sm:text-[18px] max-w-[340px] leading-relaxed font-medium">
            Від реєстрації до першого сповіщення — менше 10 хвилин
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-5">
          {STEPS.map(({ title, description, cta, href, image }) => (
            <article
              key={title}
              className="group relative flex min-h-[380px] sm:min-h-[440px] flex-col justify-between overflow-hidden rounded-[1.75rem] p-6 sm:p-7"
            >
              <Image
                src={image}
                alt=""
                fill
                className="object-cover transition-transform duration-700 motion-safe:group-hover:scale-105"
                sizes="(max-width: 768px) 100vw, 33vw"
              />
              <div className="absolute inset-0 bg-gradient-to-b from-ink/90 via-ink/55 to-ink/25" />
              <div className="absolute inset-0 bg-gradient-to-t from-ink/80 via-transparent to-transparent" />

              <div className="relative z-10">
                <h3 className="text-[24px] sm:text-[26px] font-bold leading-tight tracking-tight text-white">
                  {title}
                </h3>
                <p className="mt-2.5 max-w-[280px] text-[14px] leading-snug text-white/75">
                  {description}
                </p>
              </div>

              <div className="relative z-10 mt-6 flex justify-center">
                <CtaLink href={href} variant="emerald" size="md" className="!text-[14px] !px-5 !py-2.5">
                  {cta}
                </CtaLink>
              </div>
            </article>
          ))}
        </div>
      </div>
    </section>
  );
}
