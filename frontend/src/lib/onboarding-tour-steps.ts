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

/**
 * Інтерактивний тур кабінетом. Кроки з target підсвічують елемент [data-tour="…"].
 * Запускається при першому вході або з «Пройти інструкції ще раз» у профілі.
 */
export const ONBOARDING_TOUR_STEPS: OnboardingTourStep[] = [
  {
    id: "welcome",
    path: DASHBOARD,
    section: "Старт",
    title: "Ласкаво просимо в Carbit!",
    description:
      "Коротко покажемо кабінет: як шукати авто на ринку, зберігати моніторинг і отримувати нові лоти в Telegram раніше за конкурентів.",
    tips: [
      "Можна пройти всі кроки або натиснути «Розберуся сам»",
      "Тур сам відкриє потрібні розділи — нічого шукати в меню",
      "Повторити інструкції можна будь-коли в Акаунті → Допомога",
    ],
    placement: "center",
  },
  {
    id: "hero",
    path: DASHBOARD,
    target: "welcome-hero",
    section: "Пошук",
    title: "Ваш робочий стіл",
    description:
      "Зверху — стан кабінету: тариф, скільки моніторингів зайнято і які джерела працюють (AUTO.RIA, OLX, Telegram).",
    tips: [
      "Якщо Telegram ще не підключений — з’явиться підказка під цим блоком",
      "На free-плані тут же є швидкий перехід до підписки",
    ],
    placement: "bottom",
  },
  {
    id: "filters",
    path: DASHBOARD,
    target: "search-filters",
    section: "Пошук",
    title: "Фільтри ринку",
    description:
      "Оберіть марку, модель, рік, бюджет і регіон. Саме за цими критеріями Carbit обійде ринок.",
    tips: [
      "Спочатку «Шукати» — побачите живі оголошення і прогрес пошуку",
      "«Тільки нові / Усі пропозиції» змінює режим, але не запускає пошук автоматично — натисніть «Шукати»",
      "«Розширений пошук» — пробіг, КПП, тип кузова",
    ],
    placement: "bottom",
  },
  {
    id: "save",
    path: DASHBOARD,
    target: "save-search",
    section: "Пошук",
    title: "Збережіть як моніторинг",
    description:
      "Коли підбірка влаштовує — підключіть моніторинг. Carbit перевірятиме ринок 24/7 і ловитиме нові оголошення.",
    tips: [
      "Поточні авто з першого пошуку також потрапляють у моніторинг",
      "Нові збіги — в Telegram і в розділі «Сповіщення»",
      "Ліміт активних моніторингів залежить від тарифу",
    ],
    placement: "top",
  },
  {
    id: "searches",
    path: DASHBOARD,
    target: "my-searches",
    section: "Моніторинги",
    title: "Короткий список на головній",
    description:
      "Тут — ваші активні запити. Повний список і картки авто — у вкладці «Мої моніторинги».",
    tips: [
      "Бейдж із цифрою — скільки нових авто з’явилось",
      "Відкрийте моніторинг, щоб переглянути всі зібрані лоти",
    ],
    placement: "top",
  },
  {
    id: "monitors",
    path: "/app/monitors",
    target: "tour-section-monitors",
    section: "Моніторинги",
    title: "Усі моніторинги",
    description:
      "Центральне місце для керування запитами: скільки слотів лишилось, які активні, де з’явились нові авто.",
    tips: [
      "Якщо ліміт вичерпано — запропонуємо апгрейд тарифу",
      "Новий моніторинг зручно створити з головного екрана «Пошук»",
    ],
    placement: "bottom",
  },
  {
    id: "notifications",
    path: "/app/notifications",
    target: "tour-section-notifications",
    section: "Сповіщення",
    title: "Стрічка нових збігів",
    description:
      "Кожне нове авто з моніторингів потрапляє сюди — з фото, ціною та деталями.",
    tips: [
      "Непрочитані виділені — зручно пройтися вранці",
      "Підключіть Telegram в акаунті, щоб дублювати сповіщення в бот",
    ],
    placement: "bottom",
  },
  {
    id: "favorites",
    path: "/app/favorites",
    target: "tour-section-favorites",
    section: "Обране",
    title: "Закладки на авто",
    description:
      "Сердечко на картці оголошення — і лот у обраному. Повертайтесь сюди, коли порівнюєте варіанти.",
    tips: [
      "Список синхронізується між пристроями",
      "Зручно тримати «гарячі» авто перед дзвінком продавцю",
    ],
    placement: "bottom",
  },
  {
    id: "account",
    path: "/app/account",
    target: "tour-section-stats",
    section: "Акаунт",
    title: "Профіль і огляд",
    description:
      "Тут ім’я, валюта цін, статистика за день і ліміт моніторингів. Нижче — підписка, оплата та Telegram.",
    tips: [
      "Валюта впливає на відображення цін у кабінеті й у боті",
      "Розділи згруповані: профіль → огляд → підписка → сповіщення",
    ],
    placement: "top",
  },
  {
    id: "telegram",
    path: "/app/account",
    target: "tour-section-telegram",
    section: "Акаунт",
    title: "Telegram — ваш сигнал",
    description:
      "Без бота сповіщення лишаються лише в кабінеті. З ботом нові лоти приходять миттєво в месенджер.",
    tips: [
      "«Підключити» → Start у Telegram",
      "Можна відключити будь-коли в цьому ж блоці",
    ],
    placement: "top",
  },
  {
    id: "billing",
    path: "/app/billing",
    target: "tour-section-billing",
    section: "Підписка",
    title: "Тарифи під ваші задачі",
    description:
      "Більше активних моніторингів — на вищому тарифі. Оплата через LiqPay, скасування автопродовження в один клік.",
    tips: [
      "Старт · Про · Бізнес — оберіть за кількістю пошуків",
      "При апгрейді залишок днів поточного тарифу зараховується в доплату",
      "Ліміт видно в профілі й у боковому меню",
    ],
    placement: "bottom",
  },
  {
    id: "finish",
    path: DASHBOARD,
    section: "Готово",
    title: "Все готово — час ловити авто",
    description:
      "Налаштуйте фільтри, збережіть моніторинг і підключіть Telegram. Carbit буде шукати за вас цілодобово.",
    tips: [
      "Почніть з марки та бюджету — решту можна звузити пізніше",
      "Інструкції знову: Акаунт → Допомога → «Пройти інструкції ще раз»",
    ],
    placement: "center",
  },
];
