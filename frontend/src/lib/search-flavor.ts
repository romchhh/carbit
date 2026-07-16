/** Креативні тексти під час live-пошуку — без «технічного» тону. */

export const SEARCH_LABELS = [
  "Обходимо всі авторинки України…",
  "Торгуємося на автобазарі…",
  "Заглядаємо під капот кожній пропозиції…",
  "Ганяємо між AUTO.RIA, OLX і Telegram…",
  "Шукаємо «ту саму» серед тисяч оголошень…",
  "Питаємо продавців, чи торг доречний…",
  "Перевіряємо свіжі лоти, поки кава ще тепла…",
  "Скануємо ринок, ніби це радар, а не сайт…",
] as const;

export const SEARCH_HINTS = [
  "Ходимо між рядами, стукаємо по бамперах і відсіюємо відвертий треш.",
  "Один дивиться прайс, інший — пробіг, третій уже торгується за каву.",
  "Як на справжньому авторинку: шум, торг і шанс на хороший лот.",
  "Поки ви чекаєте — ми вже в іншому кінці «базару» з новим оголошенням.",
  "Фільтри в руках, капелюх набакир — класика полювання на авто.",
  "Ніяких нудних «завантаження 20 штук» — лише справжній пошук.",
] as const;

export const SEARCH_REFRESH_LABELS = [
  "Пересортовуємо лоти свіжішим боком…",
  "Трясемо видачу, щоб найкращі піднялись угору…",
  "Ще раз пробігаємось по ринку з новими правилами…",
] as const;

export const SEARCH_LOAD_MORE_LABELS = [
  "Йдемо далі по ряду — ще є цікаве…",
  "Відкриваємо наступну алею авторинку…",
  "Підтягуємо ще трохи лотів з базару…",
  "Не зупиняємось: далі теж є чим поласувати…",
] as const;

function pick<T>(items: readonly T[], salt = 0): T {
  const index = Math.abs(salt) % items.length;
  return items[index]!;
}

/** Стабільний вибір на сесію пошуку (не стрибає на кожен ререндер). */
export function flavorForSearch(seed: number) {
  return {
    label: pick(SEARCH_LABELS, seed),
    hint: pick(SEARCH_HINTS, seed + 3),
  };
}

export function flavorForRefresh(seed: number) {
  return pick(SEARCH_REFRESH_LABELS, seed);
}

export function flavorForLoadMore(seed: number) {
  return pick(SEARCH_LOAD_MORE_LABELS, seed);
}
