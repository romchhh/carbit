export type PricingPlan = {
  name: string;
  price: string;
  period: string;
  features: string[];
  missing: string[];
  cta: string;
  href: string;
  accent: boolean;
  popular: boolean;
};

export const PRICING_PLANS: PricingPlan[] = [
  {
    name: "Безкоштовно",
    price: "0",
    period: "7 днів тест-драйв",
    features: ["1 пошуковий запит", "Оновлення раз на годину", "Вебкабінет"],
    missing: ["Telegram-бот", "Анти-дубль", "Оцінка ризиків", "Пріоритет"],
    cta: "Почати безкоштовно",
    href: "/auth/login",
    accent: false,
    popular: false,
  },
  {
    name: "Lite",
    price: "500",
    period: "грн / місяць",
    features: ["3 пошукових запити", "Оновлення кожні 30 хв", "Telegram-бот", "Анти-дубль"],
    missing: ["Оцінка ризиків", "Пріоритетна підтримка"],
    cta: "Вибрати Lite",
    href: "/auth/login?plan=lite",
    accent: false,
    popular: false,
  },
  {
    name: "Стандарт",
    price: "2 000",
    period: "грн / місяць",
    features: [
      "10 пошукових запитів",
      "Оновлення кожні 5 хв",
      "Telegram-бот",
      "Анти-дубль",
      "Оцінка ризиків",
      "Експорт Excel",
    ],
    missing: [],
    cta: "Вибрати Стандарт",
    href: "/auth/login?plan=standard",
    accent: true,
    popular: true,
  },
  {
    name: "Pro",
    price: "6 000",
    period: "грн / місяць",
    features: [
      "50 запитів",
      "Оновлення в реальному часі",
      "Telegram-бот",
      "Анти-дубль",
      "Оцінка ризиків",
      "Повний API-доступ",
      "Персональний менеджер",
      "Підтримка 24/7",
    ],
    missing: [],
    cta: "Зв'язатися",
    href: "/contact",
    accent: false,
    popular: false,
  },
];

export const PRICING_COMPARE = [
  { feature: "Пошукові запити", free: "1", lite: "3", std: "10", pro: "50" },
  { feature: "Частота оновлення", free: "1 год", lite: "30 хв", std: "5 хв", pro: "Реал-тайм" },
  { feature: "Telegram-бот", free: false, lite: true, std: true, pro: true },
  { feature: "Анти-дубль", free: false, lite: true, std: true, pro: true },
  { feature: "Оцінка ризиків", free: false, lite: false, std: true, pro: true },
  { feature: "Експорт Excel/CSV", free: false, lite: false, std: true, pro: true },
  { feature: "API-доступ", free: false, lite: false, std: false, pro: true },
  { feature: "Персональний менеджер", free: false, lite: false, std: false, pro: true },
] as const;

export const PRICING_PLAN_HEADERS = ["Безкоштовно", "Lite", "Стандарт", "Pro"] as const;
