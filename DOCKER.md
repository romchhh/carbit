# Carbit — Docker на сервері

Короткий гайд: встановлення, запуск, перезапуск і оновлення.

## Що піднімається

| Сервіс   | Контейнер         | Порт (за замовч.) |
|----------|-------------------|-------------------|
| Backend  | `carbit-backend`  | 8000              |
| Frontend | `carbit-frontend` | 3000              |
| Bot      | `carbit-bot`      | —                 |

База SQLite зберігається на хості в папці `./database/`.

---

## Вимоги на сервері

- Docker Engine 24+
- Docker Compose v2 (`docker compose`)
- Git
- Відкриті порти **3000** (сайт) і **8000** (API), або reverse proxy (Nginx/Caddy)

---

## 1. Перше встановлення

```bash
# Клонувати проєкт
git clone <URL-репозиторію> carbit
cd carbit

# Налаштувати змінні середовища
cp .env.example .env
nano .env   # обов'язково змініть SECRET_KEY, ADMIN_PASSWORD, INTERNAL_API_SECRET, TELEGRAM_BOT_TOKEN

# Створити папку для БД
mkdir -p database

# Зібрати і запустити
docker compose up -d --build
```

Перевірка:

```bash
docker compose ps
curl http://localhost:8000/health
curl -I http://localhost:3000
```

---

## 2. Налаштування `.env` для production

Мінімум для сервера:

```env
SECRET_KEY=<довгий-випадковий-ключ>
FRONTEND_URL=https://your-domain.com

NEXT_PUBLIC_API_URL=https://your-domain.com/api/v1
# або якщо API на окремому піддомені:
# NEXT_PUBLIC_API_URL=https://api.your-domain.com/api/v1

GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback

TELEGRAM_BOT_TOKEN=...
TELEGRAM_BOT_USERNAME=your_bot
INTERNAL_API_SECRET=<спільний-секрет>

# BACKEND_URL для бота всередині Docker задається в docker-compose.yml автоматично:
# http://backend:8000/api/v1
```

> **Важливо:** `NEXT_PUBLIC_API_URL` підставляється під час **збірки** frontend-образу. Якщо змінили URL — потрібен rebuild frontend (див. розділ «Оновлення»).

Опційно змінити порти на хості:

```env
FRONTEND_PORT=3000
BACKEND_PORT=8000
```

---

## 3. Запуск

```bash
docker compose up -d
```

З логами в терміналі (без `-d`):

```bash
docker compose up
```

---

## 4. Перезапуск

Усі сервіси:

```bash
docker compose restart
```

Окремий сервіс:

```bash
docker compose restart backend
docker compose restart frontend
docker compose restart bot
```

---

## 5. Оновлення на сервері

```bash
cd carbit

# Отримати новий код
git pull

# Перезібрати образи і застосувати
docker compose up -d --build

# Перевірити статус
docker compose ps
```

Якщо змінилися тільки Python-залежності або backend/bot:

```bash
docker compose up -d --build backend bot
```

Якщо змінився `NEXT_PUBLIC_API_URL` або frontend:

```bash
docker compose build frontend
docker compose up -d frontend
```

---

## 6. Логи і діагностика

```bash
# Усі сервіси
docker compose logs -f

# Окремий сервіс
docker compose logs -f backend
docker compose logs -f bot
docker compose logs -f frontend
```

---

## 7. Зупинка

```bash
# Зупинити контейнери (дані в database/ залишаються)
docker compose down

# Зупинити і видалити volumes compose (НЕ видаляє ./database на хості)
docker compose down -v
```

---

## 8. Резервна копія БД

```bash
# Зупинити backend (рекомендовано для консистентності)
docker compose stop backend bot

# Скопіювати файли
cp database/autoradar.db database/autoradar.db.bak.$(date +%F)
cp database/kv.db database/kv.db.bak.$(date +%F)

# Запустити знову
docker compose start backend bot
```

---

## 9. Reverse proxy (Nginx) — коротко

Приклад маршрутизації:

- `your-domain.com` → `http://127.0.0.1:3000` (frontend)
- `your-domain.com/api/` → `http://127.0.0.1:8000/api/` (backend)

Тоді в `.env`:

```env
FRONTEND_URL=https://your-domain.com
NEXT_PUBLIC_API_URL=https://your-domain.com/api/v1
GOOGLE_REDIRECT_URI=https://your-domain.com/api/v1/auth/google/callback
```

Після зміни — `docker compose up -d --build frontend`.

---

## 10. Типові проблеми

| Симптом | Рішення |
|---------|---------|
| Backend unhealthy / Restarting | `docker compose logs backend --tail=50` — часто бракує `storage/` в образі (оновіть код і `--build`) |
| `ModuleNotFoundError: storage` | `git pull && docker compose up -d --build backend bot` |
| Frontend не бачить API | Перевірте `NEXT_PUBLIC_API_URL`, перезберіть frontend |
| Bot не підключається до backend | `INTERNAL_API_SECRET` однаковий у `.env`; bot використовує `BACKEND_URL` з compose |
| CORS помилки | Додайте домен у `ALLOWED_ORIGINS` у `backend/app/core/config.py` |
| Порт зайнятий | Змініть `FRONTEND_PORT` / `BACKEND_PORT` у `.env` |

---

## Корисні команди (шпаргалка)

```bash
docker compose up -d --build    # перша збірка / повне оновлення
docker compose ps                 # статус
docker compose restart            # перезапуск
docker compose logs -f backend    # логи
docker compose down               # зупинка
```
