# Carbit — Docker на сервері

Короткий гайд: встановлення, запуск, перезапуск і оновлення.

## Що піднімається

| Сервіс   | Контейнер         | Порт (за замовч.) |
|----------|-------------------|-------------------|
| Postgres | `carbit-postgres` | 5432 (внутрішній) |
| Backend  | `carbit-backend`  | 8000              |
| Frontend | `carbit-frontend` | 3000              |
| Bot      | `carbit-bot`      | —                 |

Основна БД — **PostgreSQL**. Legacy-файл `database/autoradar.db` (SQLite) зберігається на хості; при першому старті backend **автоматично імпортує** дані в Postgres (позначка `database/.postgres_imported_from_sqlite`).

---

## Вимоги на сервері

- Docker Engine 24+
- Docker Compose v2 (`docker compose`)
- Git
- Відкриті порти **3000** (сайт) і **8000** (API), або reverse proxy (Nginx/Caddy)

---

## 0. Ліміт build cache (один раз на сервері)

BuildKit накопичує шари з кожного білда і сам їх не чистить — через це диск може забитися, і `docker compose build` почне падати.

**Один раз після встановлення Docker** на production-хості:

```bash
sudo ./scripts/setup-docker-cache-limits.sh
```

Скрипт:

- вмикає автоматичний GC BuildKit з лімітом **2GB** (`/etc/docker/daemon.json`);
- обмежує розмір логів контейнерів (`max-size: 10m`, `max-file: 3`);
- додає cron — щонеділі о 04:00 чистить build cache старіший за 7 днів;
- одразу прибирає старий reclaimable cache.

Інший ліміт (наприклад 4GB):

```bash
sudo DOCKER_BUILD_CACHE_LIMIT=4GB ./scripts/setup-docker-cache-limits.sh
```

Перевірка:

```bash
docker builder du
```

Ручна чистка (якщо потрібно):

```bash
docker builder prune -af --filter "until=168h"
```

> **Не використовуйте `--no-cache`** для звичайних деплоїв — це будує з нуля і додає зайві шари поверх старого кешу. `--no-cache` лише якщо підозра на зіпсований кеш.

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

# Ліміт build cache (один раз)
sudo ./scripts/setup-docker-cache-limits.sh

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
# або відносний шлях (рекомендовано, якщо API на тому ж домені):
# NEXT_PUBLIC_API_URL=/api/v1

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

## Перехід з SQLite на PostgreSQL

Після оновлення коду:

1. Переконайтесь, що `database/autoradar.db` на хості **не видалений** (з нього імпорт).
2. У `.env` вкажіть:
   ```env
   DATABASE_URL=postgresql+asyncpg://carbit:carbit@postgres:5432/carbit
   ```
3. Перезберіть і підніміть стек:
   ```bash
   docker compose up -d --build
   ```
4. У логах backend має з’явитись `[sqlite→postgres] OK: finished ...` або `SKIP: ...` з причиною.

**Діагностика та ручний імпорт (на VPS, без venv):**

```bash
# Статус: шляхи, кількість рядків у sqlite vs postgres
./scripts/migrate-sqlite-to-postgres.sh --status

# Імпорт / merge (якщо в sqlite більше даних — запуститься автоматично)
./scripts/migrate-sqlite-to-postgres.sh --force
```

Або напряму:

```bash
docker compose exec backend python /app/backend/scripts/migrate_sqlite_to_postgres.py --status
docker compose exec backend python /app/backend/scripts/migrate_sqlite_to_postgres.py --force
```

5. Після успіху створюється `database/.postgres_imported_from_sqlite`.

```bash
SQLITE_MIGRATE_FORCE=1 docker compose up -d --build backend
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
./scripts/docker-deploy.sh
```

Або вручну:

```bash
git pull
docker compose build
docker compose up -d
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
| `POST .../auto-ria/search` → 404 | Старий backend-образ. `git pull && docker compose build backend && docker compose up -d backend`. Перевірка: `curl -s localhost:8000/health` → `auto_ria_live_route: true` |
| Build падає / «no space left» | `docker builder du` — якщо кеш великий: `sudo ./scripts/setup-docker-cache-limits.sh` або `docker builder prune -af --filter "until=168h"` |
| Повільний або «зіпсований» білд | Лише тоді: `docker compose build --no-cache <service>` |
| Mixed Content / `http://backend:8000` у консолі | Неправильний `NEXT_PUBLIC_API_URL` у `.env`. Має бути `/api/v1` або `https://ваш-домен/api/v1`. Потім `docker compose up -d --build frontend` |
| Кабінет відкривається, але пошук дає 401 | Старий Bearer у localStorage + cookie. Оновіть backend/frontend: fallback cookie і API proxy. Або вийдіть і зайдіть знову. |
| `GET /api/v1/fx/rates` → 404 | Старий backend без `fx` router. `docker compose up -d --build backend` |
| Frontend не бачить API | Перевірте `NEXT_PUBLIC_API_URL`, перезберіть frontend |
| Bot не підключається до backend | `INTERNAL_API_SECRET` однаковий у `.env`; bot використовує `BACKEND_URL` з compose |
| CORS помилки | Додайте домен у `ALLOWED_ORIGINS` у `backend/app/core/config.py` |
| Порт зайнятий | Змініть `FRONTEND_PORT` / `BACKEND_PORT` у `.env` |

---

## Корисні команди (шпаргалка)

```bash
./scripts/docker-deploy.sh        # git pull + build + up (без --no-cache)
docker compose up -d --build      # перша збірка / повне оновлення
docker builder du                 # розмір build cache
docker compose ps                 # статус
docker compose restart            # перезапуск
docker compose logs -f backend    # логи
docker compose down               # зупинка
```
