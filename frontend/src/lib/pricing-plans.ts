export type PricingPlan = {
  id: string;
  name: string;
  description: string;
  price: string;
  period: string;
  features: string[];
  missing: string[];
  cta: string;
  href: string;
  accent: boolean;
  popular: boolean;
};

/** Платні пакети — актуальні ціни (не нуль) для LiqPay / вітрини. */
export const PRICING_PLANS: PricingPlan[] = [
  {
    id: "free",
    name: "Безкоштовно",
    description: "Пробний доступ до сервісу моніторингу оголошень авторинку.",
    price: "0",
    period: "7 днів",
    features: [
      "Пробний період 7 днів",
      "До 1 активного моніторингу",
      "1 акаунт",
      "Веб-кабінет і сповіщення",
    ],
    missing: [],
    cta: "Почати безкоштовно",
    href: "/auth/login",
    accent: false,
    popular: false,
  },
  {
    id: "lite",
    name: "Старт",
    description:
      "Підписка на 30 днів: моніторинг оголошень авторинку з до 10 активними пошуками для 1 акаунту.",
    price: "390",
    period: "грн / 30 днів",
    features: [
      "30 днів доступу",
      "До 10 активних моніторингів",
      "1 акаунт",
      "Telegram-сповіщення",
      "Веб-кабінет",
    ],
    missing: [],
    cta: "Обрати Старт",
    href: "/auth/login?plan=lite",
    accent: false,
    popular: false,
  },
  {
    id: "standard",
    name: "Про",
    description:
      "Підписка на 30 днів: до 30 активних моніторингів і до 3 акаунтів для команди підбірників.",
    price: "790",
    period: "грн / 30 днів",
    features: [
      "30 днів доступу",
      "До 30 активних моніторингів",
      "До 3 акаунтів",
      "Telegram-сповіщення",
      "Анти-дубль оголошень",
    ],
    missing: [],
    cta: "Обрати Про",
    href: "/auth/login?plan=standard",
    accent: true,
    popular: true,
  },
  {
    id: "pro",
    name: "Бізнес",
    description:
      "Підписка на 30 днів: до 100 активних моніторингів і до 5 акаунтів для великих команд.",
    price: "1 790",
    period: "грн / 30 днів",
    features: [
      "30 днів доступу",
      "До 100 активних моніторингів",
      "До 5 акаунтів",
      "Telegram-сповіщення",
      "Пріоритетна обробка пошуків",
    ],
    missing: [],
    cta: "Обрати Бізнес",
    href: "/auth/login?plan=pro",
    accent: false,
    popular: false,
  },
];

export const PRICING_COMPARE = [
  { feature: "Тривалість", free: "7 днів", lite: "30 днів", std: "30 днів", pro: "30 днів" },
  { feature: "Ціна", free: "Безкоштовно", lite: "390 грн", std: "790 грн", pro: "1 790 грн" },
  { feature: "Активні моніторинги", free: "1", lite: "10", std: "30", pro: "100" },
  { feature: "Акаунти", free: "1", lite: "1", std: "до 3", pro: "до 5" },
  { feature: "Telegram-сповіщення", free: true, lite: true, std: true, pro: true },
  { feature: "Веб-кабінет", free: true, lite: true, std: true, pro: true },
  { feature: "Анти-дубль", free: false, lite: false, std: true, pro: true },
  { feature: "Пріоритетна обробка", free: false, lite: false, std: false, pro: true },
] as const;

export const PRICING_PLAN_HEADERS = ["Безкоштовно", "Старт", "Про", "Бізнес"] as const;

export const SUPPORT_EMAIL = "info@13vplus.com";
