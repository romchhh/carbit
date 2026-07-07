export type TourPlacement = "top" | "bottom" | "left" | "right" | "center";

export type OnboardingTourStep = {
  id: string;
  path?: string;
  target?: string;
  section?: string;
  title: string;
  description: string;
  tips?: string[];
  placement?: TourPlacement;
};

const DASHBOARD = "/app/dashboard";

export const ONBOARDING_TOUR_STEPS: OnboardingTourStep[] = [
  {
    id: "welcome",
    path: DASHBOARD,
    section: "Старт",
    title: "Ласкаво просимо в Carbit!",
    description:
      "За хвилину покажемо, як налаштувати моніторинг авто та отримувати нові оголошення раніше за інших.",
    tips: [
      "Можна пройти всі кроки або натиснути «Розберуся сам»",
      "Тур відкриє кожен розділ кабінету по черзі",
    ],
    placement: "center",
  },
  {
    id: "hero",
    path: DASHBOARD,
    target: "welcome-hero",
    section: "Головна",
    title: "Огляд кабінету",
    description: "Тут бачите загальний стан: скільки моніторингів активно та які джерела підключені.",
    tips: [
      "AUTO.RIA, OLX і Telegram — все в одному місці",
      "Якщо Telegram не підключений — зʼявиться підказка внизу",
    ],
    placement: "bottom",
  },
  {
    id: "filters",
    path: DASHBOARD,
    target: "search-filters",
    section: "Головна",
    title: "Налаштуйте фільтри",
    description: "Оберіть марку, модель, рік, бюджет і регіон — саме за цими критеріями шукатимемо авто.",
    tips: [
      "Спочатку натисніть «Шукати», щоб побачити приклади",
      "«Розширений пошук» — пробіг, КПП, тип кузова",
    ],
    placement: "bottom",
  },
  {
    id: "save",
    path: DASHBOARD,
    target: "save-search",
    section: "Головна",
    title: "Збережіть моніторинг",
    description: "Коли фільтри влаштовують — збережіть запит. Carbit почне перевіряти джерела 24/7.",
    tips: [
      "Після збереження нові авто приходитимуть автоматично",
      "Ліміт запитів залежить від тарифу",
    ],
    placement: "top",
  },
  {
    id: "searches",
    path: DASHBOARD,
    target: "my-searches",
    section: "Головна",
    title: "Мої запити",
    description: "Усі збережені моніторинги — з лічильником знайдених авто та швидким переходом до результатів.",
    tips: [
      "Зелена крапка — запит активний",
      "«Результати» — повний список авто за цим запитом",
    ],
    placement: "top",
  },
  {
    id: "notifications",
    path: "/app/notifications",
    target: "tour-section-notifications",
    section: "Сповіщення",
    title: "Нові збіги тут",
    description: "Кожне нове авто з ваших моніторингів зʼявляється в цьому розділі — з карткою та деталями.",
    tips: [
      "Непрочитані виділені зеленим",
      "Підключіть Telegram в акаунті — дублюватимемо в бот",
      "Сортуйте за ціною, роком або пробігом",
    ],
    placement: "bottom",
  },
  {
    id: "favorites",
    path: "/app/favorites",
    target: "tour-section-favorites",
    section: "Обране",
    title: "Закладки на авто",
    description: "Додавайте цікаві лоти в обране з будь-якої картки — повертатись до них зручно звідси.",
    tips: [
      "Натисніть сердечко на картці оголошення",
      "Список синхронізується між пристроями",
    ],
    placement: "bottom",
  },
  {
    id: "stats",
    path: "/app/stats",
    target: "tour-section-stats",
    section: "Статистика",
    title: "Ваша активність",
    description: "Зведення по кабінету: скільки запитів активно, скільки нових авто сьогодні та що в обраному.",
    tips: [
      "Корисно оцінити, наскільки «живі» ваші фільтри",
      "Тут же видно поточний тариф",
    ],
    placement: "bottom",
  },
  {
    id: "account",
    path: "/app/account",
    target: "tour-section-telegram",
    section: "Акаунт",
    title: "Профіль і Telegram",
    description: "Редагуйте імʼя, дивіться тариф і підключайте бота — щоб отримувати авто прямо в месенджер.",
    tips: [
      "«Підключити» → Start у боті — і готово",
      "Без Telegram сповіщення лишаються лише в кабінеті",
    ],
    placement: "top",
  },
  {
    id: "billing",
    path: "/app/billing",
    target: "tour-section-billing",
    section: "Підписка",
    title: "Тарифи та ліміти",
    description: "Більше збережених запитів — на вищому тарифі. Trial дає повний доступ на старті.",
    tips: [
      "7 днів безкоштовно без карти",
      "Ліміт запитів видно в боковому меню (десктоп)",
    ],
    placement: "bottom",
  },
  {
    id: "finish",
    path: DASHBOARD,
    section: "Готово",
    title: "Все готово!",
    description: "Створіть перший моніторинг — і Carbit почне шукати авто за вас.",
    tips: [
      "Почніть з марки та бюджету, решту можна звузити пізніше",
      "Успіхів у пошуку ідеального авто!",
    ],
    placement: "center",
  },
];
