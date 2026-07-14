# LiqPay: рекурентні (підписочні) платежі — технічний гайд

Джерело: офіційна документація LiqPay (liqpay.ua/doc/api) + офіційний приклад API `subscribe`.

---

## 1. Як влаштована підписка в LiqPay

LiqPay не має окремого "Subscriptions API" з CRUD-об'єктом підписки — рекурент реалізується через **звичайний платіж з прапорцем `subscribe`**. Перший запит одночасно:
- проводить перший платіж (або холд токена картки),
- зберігає токен картки клієнта на стороні LiqPay,
- реєструє розклад автоматичних списань за цим `order_id`.

Далі LiqPay сам знімає гроші за розкладом і на кожне списання шле `callback` на твій `server_url`.

Дії (action), які тобі потрібні:

| action | Призначення |
|---|---|
| `subscribe` | Створити підписку (перший платіж + розклад) |
| `subscribe_update` | Змінити суму/опис активної підписки |
| `unsubscribe` | Скасувати підписку (наступні списання не проводяться) |
| `status` | Перевірити поточний статус платежу/підписки за `order_id` |

Ендпоінт для всіх — **server-server**: `POST https://www.liqpay.ua/api/request`
(це той самий метод, що і для звичайного `pay`, `hold` і т.д.)

---

## 2. Як отримати ключі (public_key / private_key)

1. Заходиш у кабінет LiqPay → **Бізнес → [назва компанії] → Налаштування → API** (або одразу видно на головній сторінці кабінету після реєстрації компанії).
2. Там два режими:
   - **Тестовий режим** (перемикач у кабінеті) — показує **sandbox-ключі**, вони завжди мають префікс `sandbox_`. Ними можна імітувати оплати без реального списання коштів.
   - **Бойовий режим** — реальні `public_key` / `private_key`, з'являються **після проходження активації компанії** (модерація магазину LiqPay).
3. У тебе вже є тестовий ключ:
   ```
   sandbox_LDn1XkqgEJ7POKRqTSQVdBpRaw0x43USeZ17U1l4
   ```
   Зверни увагу: в кабінеті буде **дві** пари ключів — public і private, обидві з префіксом `sandbox_`. Той, що ти скинув — це, скоріш за все, один з них (треба звірити в кабінеті, який саме public, а який private — не переплутай при інтеграції).
4. Посилання `https://www.liqpay.ua/uk/checkout/sandbox_i94596637647` — це тестове checkout-посилання (демо-сторінка оплати), не плутати з ключем API.
5. Для production-ключів компанія має бути **активована** (розділ "Активація компанії" в кабінеті — реквізити, документи ФОП, підтвердження сайту з офертою тощо). Тобі це актуально, бо ти вже "активував компанію" — тобто бойові ключі мають з'явитись на головній сторінці кабінету LiqPay.

---

## 3. Створення підписки — `subscribe`

### Параметри запиту

| Параметр | Обов'язковий | Опис |
|---|---|---|
| `action` | так | `"subscribe"` |
| `version` | так | `"3"` |
| `public_key` | так | твій публічний ключ |
| `amount` | так | сума одного платежу |
| `currency` | так | `UAH`, `USD`, `EUR` |
| `description` | так | опис платежу |
| `order_id` | так | унікальний ID **саме цієї підписки** в твоїй системі (по ньому далі йдуть `subscribe_update`/`unsubscribe`/`status`) |
| `subscribe` | так | `"1"` — прапорець, що це підписка |
| `subscribe_date_start` | так | дата початку, формат `"YYYY-MM-DD HH:MM:SS"` |
| `subscribe_periodicity` | так | періодичність: `"month"` або `"year"` (LiqPay офіційно підтримує саме ці два значення) |
| `card`, `card_exp_month`, `card_exp_year`, `card_cvv` | так (якщо server-server з введенням картки напряму) | дані картки клієнта — **вимагає PCI DSS сертифікації**, якщо картка вводиться на твоєму бекенді |
| `server_url` | рекомендовано | URL, куди LiqPay шле callback на кожне списання |
| `result_url` | опційно | куди редіректнути клієнта після оплати (для Client-Server флоу) |

### Важливо про PCI DSS

Якщо клієнт вводить дані картки (`card`, `card_cvv`) безпосередньо на твоєму сервері (Server-Server) — тобі формально потрібна сертифікація PCI DSS. **Практичний і найпоширеніший варіант для агентства без PCI DSS**: використовувати **Checkout / Payment Widget (Client-Server)** — клієнт вводить картку на сторінці LiqPay, ти отримуєш назад `card_token`, і далі всі подальші списання (продовження підписки, `subscribe_update`) робиш через токен, не торкаючись самих даних картки.

Тобто послідовність для реальних інтеграцій:
1. Перший платіж — через Checkout (`https://www.liqpay.ua/api/3/checkout`) з `recurringbytoken: "1"` — клієнт вводить картку на сторінці LiqPay.
2. В callback на `server_url` отримуєш `card_token`.
3. Зберігаєш `card_token` у своїй БД.
4. Наступні рекурентні списання робиш `action: "pay"` з цим `card_token` (без введення картки заново) — або одразу створюєш `subscribe` з `recurringbytoken`, якщо потрібен саме автоматичний розклад на стороні LiqPay.

### Приклад запиту (офіційний, bash/curl)

```bash
PUBLIC_KEY='your_public_key'
PRIVATE_KEY='your_private_key'
API_URL='https://www.liqpay.ua/api/request'

JSON="{
  \"action\" : \"subscribe\",
  \"version\" : 3,
  \"public_key\" : \"${PUBLIC_KEY}\",
  \"amount\" : 100,
  \"currency\" : \"UAH\",
  \"description\" : \"Щомісячна підписка\",
  \"order_id\" : \"sub_12345\",
  \"subscribe\" : \"1\",
  \"subscribe_date_start\" : \"2026-07-15 00:00:00\",
  \"subscribe_periodicity\" : \"month\",
  \"server_url\" : \"https://yourdomain.com/api/liqpay/callback\",
  \"card\" : \"4731195301524634\",
  \"card_exp_month\" : \"03\",
  \"card_exp_year\" : \"30\",
  \"card_cvv\" : \"111\"
}"

DATA=$(echo -n "${JSON}" | base64 -w0)
SIGNATURE=$(echo -n "${PRIVATE_KEY}${DATA}${PRIVATE_KEY}" | openssl dgst -binary -sha1 | base64)

curl --silent -XPOST "${API_URL}" \
  --data-urlencode data="${DATA}" \
  --data-urlencode signature="${SIGNATURE}"
```

### Python-приклад (aiohttp/requests style, актуально для твого стеку)

```python
import base64
import hashlib
import json
import requests

PUBLIC_KEY = "sandbox_xxx"
PRIVATE_KEY = "sandbox_yyy"

def liqpay_request(params: dict) -> dict:
    data_json = json.dumps(params)
    data = base64.b64encode(data_json.encode()).decode()
    sign_str = PRIVATE_KEY + data + PRIVATE_KEY
    signature = base64.b64encode(hashlib.sha1(sign_str.encode()).digest()).decode()

    resp = requests.post(
        "https://www.liqpay.ua/api/request",
        data={"data": data, "signature": signature},
    )
    return resp.json()

params = {
    "action": "subscribe",
    "version": "3",
    "public_key": PUBLIC_KEY,
    "amount": 100,
    "currency": "UAH",
    "description": "Щомісячна підписка на бота",
    "order_id": "sub_12345",
    "subscribe": "1",
    "subscribe_date_start": "2026-07-15 00:00:00",
    "subscribe_periodicity": "month",
    "server_url": "https://yourdomain.com/api/liqpay/callback",
    "card": "4731195301524634",
    "card_exp_month": "03",
    "card_exp_year": "30",
    "card_cvv": "111",
}

result = liqpay_request(params)
print(result["status"])
```

> Зверни увагу: у деяких SDK/бібліотеках підпис рахується через **sha1**, у деяких (новіші приклади документації) — через **sha3-256**. Дивись, яка версія алгоритму вказана в твоєму конкретному розділі документації (`API → Checkout` показує sha3-256, старіший `subscribe`-приклад — sha1). Якщо підпис не збігається на стороні LiqPay — спробуй обидва варіанти хешування на тестових ключах.

---

## 4. Зміна підписки — `subscribe_update`

Дозволяє змінити суму/опис уже активної підписки без її перестворення.

```json
{
  "action": "subscribe_update",
  "version": "3",
  "public_key": "your_public_key",
  "order_id": "sub_12345",
  "amount": 150,
  "currency": "UAH",
  "description": "Оновлена сума підписки"
}
```

`order_id` має бути **тим самим**, що і при створенні підписки.

---

## 5. Скасування підписки — `unsubscribe`

```json
{
  "action": "unsubscribe",
  "version": "3",
  "public_key": "your_public_key",
  "order_id": "sub_12345"
}
```

Успішна відповідь містить `"status": "unsubscribed"`. Після цього LiqPay більше не знімає гроші за цим `order_id`. Наступні списання клієнту не йдуть — але вже проведені платежі це не скасовує (для повернення коштів — окремий `action: "refund"`).

---

## 6. Контроль і моніторинг підписок

### 6.1. Callback (server_url) — головний спосіб контролю

На кожне списання (перше і всі наступні за розкладом) LiqPay шле **POST-запит** на твій `server_url` з тими самими полями `data` + `signature`, що і в звичайному callback.

Обов'язково:
1. **Перевіряй підпис** на своєму боці: `base64_encode(sha1(private_key + data + private_key))` (або sha3-256, залежно від версії) і звіряй з отриманим `signature`. Без цього будь-хто може підробити callback.
2. З `data` (це base64 → json) дивишся поля:
   - `status` — `success`, `failure`, `subscribed`, `unsubscribed`, `wait_accept` (у sandbox) тощо.
   - `order_id` — щоб знайти підписку у своїй БД.
   - `card_token` — якщо потрібно зберегти токен для подальших ручних списань.
3. Відповідай LiqPay **200 OK** швидко (без важкої обробки в цьому ж запиті) — важку логіку (оновлення БД, надсилання листів) винось у чергу/фонову задачу, щоб не тримати LiqPay в очікуванні і не отримати повторні ретраї callback.

### 6.2. Перевірка статусу вручну — `status`

Можна в будь-який момент опитати статус конкретного платежу/підписки, не чекаючи callback:

```json
{
  "action": "status",
  "version": "3",
  "public_key": "your_public_key",
  "order_id": "sub_12345"
}
```

Корисно для:
- звірки, якщо callback з якоїсь причини не дійшов (мережеві проблеми, впав сервер);
- ручної перевірки перед показом клієнту стану підписки.

### 6.3. Практична схема для контролю підписок (рекомендація)

Тримай у своїй БД таблицю підписок незалежно від LiqPay, і онови її записи через callback + періодичну звірку через `status`:

```
subscriptions
├── order_id          (унікальний, primary для зв'язку з LiqPay)
├── user_id
├── amount
├── currency
├── periodicity        (month/year)
├── status              (active, cancelled, failed, past_due)
├── next_billing_date   (розраховуєш сам на основі periodicity, LiqPay не завжди явно віддає це поле)
├── card_token
├── created_at
└── cancelled_at
```

LiqPay не дає окремого "списку всіх активних підписок компанії" по API — тому джерело правди по підписках у тебе має бути **власна БД**, синхронізована через callback + `status`. Для звірки за період можна також використовувати **Реєстр / Архів платежів** (інформаційні API LiqPay) — вони повертають список усіх прийнятих платежів компанії за період, звідки можна вивести й рекурентні списання по `order_id`.

---

## 7. Тестування (sandbox)

- У кабінеті вмикаєш **тестовий режим** — з'являються `sandbox_...` ключі, вони вже в тебе є.
- Тестова картка (стандартна для LiqPay-документації): `4731195301524634`, будь-який майбутній `card_exp_month/year`, CVV `111`.
- У sandbox статус успішного платежу може прийти як `wait_accept` — це нормально для тестового режиму, вважай його аналогом `success`.
- Твоє checkout-посилання `https://www.liqpay.ua/uk/checkout/sandbox_i94596637647` — це вже готова тестова сторінка оплати для перевірки UI-флоу, зручно для ручної перевірки перед написанням коду.

---

## 8. Короткий чекліст для інтеграції

1. [ ] Дістати з кабінету пару `public_key` / `private_key` (sandbox — вже маєш, production — після активації компанії).
2. [ ] Підняти ендпоінт `server_url` на своєму бекенді (FastAPI/aiogram-бот) для прийому callback.
3. [ ] Реалізувати перевірку підпису на callback.
4. [ ] Створити таблицю `subscriptions` у своїй БД.
5. [ ] Реалізувати `subscribe` (перший платіж + реєстрація розкладу).
6. [ ] Обробити callback: оновлення статусу, збереження `card_token`.
7. [ ] Реалізувати `unsubscribe` для відписки користувача.
8. [ ] (опційно) `subscribe_update` для зміни тарифу без пересворення підписки.
9. [ ] (опційно) Періодична звірка через `status`/Реєстр платежів — на випадок пропущених callback.
10. [ ] Протестувати весь флоу на sandbox-ключах перед переходом на бойові.

---

## 9. Офіційні розділи документації для довідки

- Підписка (Server-Server): `liqpay.ua/doc/api/internet_acquiring/subscription`
- Токени: `liqpay.ua/doc/api/tokens`
- Callback: `liqpay.ua/doc/api/callback`
- Errors: `liqpay.ua/doc/api/errors`
- Інформаційні API (статус, архів, реєстр): `liqpay.ua/doc/api/information`
- Тестування: `liqpay.ua/doc/api/testing`

> Примітка: у LiqPay точні поля іноді відрізняються між "старою" (API v3, style sha1) і "новою" (Checkout, style sha3-256) гілками документації — тому перед продакшн-запуском обов'язково звір конкретні поля прямо в кабінеті → розділ "Документація" → "Підписка", бо там можуть додавати нові параметри (наприклад підтримку Apple Pay/Google Pay в рекуренті — це окрема історія з recToken, з якою ти вже стикався на іншому проєкті через WayForPay).
