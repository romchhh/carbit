# Carbit

Агрегатор оголошень авторинку України (AUTO.RIA · OLX · Telegram).

## Стек

- **Frontend**: Next.js 15 · TypeScript · Tailwind CSS · PWA
- **Backend**: FastAPI · SQLAlchemy · SQLite
- **Bot**: Python · aiogram 3
- **Parser**: Telethon (окремий Python-модуль)

## Структура проєкту

```
autoradar/
├── .env.example          # єдиний env для всіх сервісів
├── .venv/                # Python venv (backend + bot)
├── database/             # SQLite: autoradar.db, kv.db, Telethon session
├── media/                # фото з Telegram-каналів (не в git)
├── storage/              # KV-сховище (токени, коди)
│
├── frontend/             # Next.js — лендінг, кабінет /app, адмін /admin
├── backend/              # FastAPI REST API
│   └── app/services/
│       ├── auto_ria/     # пошук через Partner API
│       ├── olx/          # парсинг HTML olx.ua
│       ├── telegram/     # Bot API (сповіщення користувачам)
│       ├── telegram_channels/  # міст між /parser і БД
│       ├── parser/       # ⚠️ пайплайн збережених пошуків (НЕ Telethon!)
│       └── search/       # об'єднаний пошук по джерелах
│
├── parser/               # Telethon-парсер Telegram-каналів
├── bot/                  # aiogram-бот (реєстрація / вхід / connect)
├── worker/               # плановий парсер (AUTO.RIA + OLX + Telegram batch)
├── telegram_worker/      # realtime-слухач нових постів у каналах
└── scripts/              # docker-deploy.sh тощо
```

### Потік даних

1. **Пошук у кабінеті** — frontend → `backend/services/search/` → AUTO.RIA / OLX / Telegram (з БД).
2. **Збережений пошук** — `worker` → `backend/services/parser/runner.py` → upsert у БД → сповіщення.
3. **Telegram-канали** — `parser/` (Telethon) → `telegram_channels/ingest.py` → БД; realtime через `telegram_worker/`.
4. **Бот** — `bot/` → internal API backend → токени в `storage/kv_store.py`.

### Авторизація (phone-first)

- **Реєстрація / вхід у UI** — лише номер телефону (`/auth/login`).
- **Реєстрація** — SMS-код через TurboSMS (`TURBOSMS_TOKEN`, `TURBOSMS_SENDER=Carbit`).
- **Вхід** — код у Telegram, якщо акаунт привʼязаний; інакше SMS.
- **Голосовий пошук** — OpenAI, тільки в кабінеті (не на лендінгу).
- **Порівняння** — `/app/compare?ids=...` доступне гостям.

## Перший запуск (локально)

```bash
cd autoradar

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # OPENAI_API_KEY, TURBOSMS_*, TELEGRAM_BOT_TOKEN, TELETHON_* …

mkdir -p database media
cd backend && PYTHONPATH=. alembic upgrade head && cd ..
```

## Запуск (3 термінали)

**Backend:**
```bash
source .venv/bin/activate
cd backend && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Bot:**
```bash
source .venv/bin/activate
cd bot && python main.py
```

**Frontend:**
```bash
cd frontend && npm install && npm run dev
```

| Сервіс | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| Admin | http://localhost:3000/admin |
| API docs | http://localhost:8000/api/docs |

**Admin login** (за замовчуванням): `admin` / `admin123` — змініть через `ADMIN_USERNAME` / `ADMIN_PASSWORD`.

**База даних**: `database/autoradar.db` · **KV**: `database/kv.db`

**Bot ↔ Backend**: `INTERNAL_API_SECRET` у `.env` має збігатися для обох сервісів.

## Docker (production)

Повна інструкція: **[DOCKER.md](./DOCKER.md)**

```bash
cp .env.example .env
mkdir -p database media
docker compose up -d --build
```

## API (`/api/v1/`)

`auth` · `users` · `searches` · `listings` · `favorites` · `notifications` · `billing` · `telegram` · `admin` · `internal/bot`

## Тести

```bash
# Parser (без Telegram)
python3 -m unittest parser.test_extractor parser.test_channel_links -q

# Backend
cd backend && PYTHONPATH=. python3 -m pytest tests/ -q
```
