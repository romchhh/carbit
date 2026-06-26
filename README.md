# AutoRadar

Агрегатор оголошень авторинку України (AUTO.RIA · OLX · Telegram).

## Стек
- **Frontend**: Next.js 15 · TypeScript · Tailwind CSS · PWA
- **Backend**: FastAPI · SQLAlchemy · SQLite
- **Bot**: Python · aiogram 3

## Структура
```
autoradar/
├── .env.example  єдиний env для backend, bot і frontend
├── .venv/        Python venv (backend + bot)
├── database/     SQLite (autoradar.db + kv.db, не в git)
├── storage/      локальне KV-сховище (коди, токени)
├── frontend/     Next.js (кабінет + /admin)
├── backend/      FastAPI REST API
├── bot/          Telegram-бот (окремий сервіс)
└── scripts/      Shell-скрипти запуску
```

## Перший запуск (один раз)

```bash
cd autoradar

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env   # заповніть TELEGRAM_BOT_TOKEN, RESEND_API_KEY тощо

mkdir -p database
cd backend && PYTHONPATH=. alembic upgrade head && cd ..
```

## Запуск

**Backend** (термінал 1):
```bash
./scripts/start-backend.sh
# або вручну:
source .venv/bin/activate && cd backend && PYTHONPATH=. uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**Bot** (термінал 2):
```bash
./scripts/start-bot.sh
# або вручну:
source .venv/bin/activate && cd bot && python main.py
```

**Frontend** (термінал 3):
```bash
cd frontend && npm install && npm run dev
```

| Сервіс | URL |
|--------|-----|
| Frontend | http://localhost:3000 |
| Admin panel | http://localhost:3000/admin |
| API docs | http://localhost:8000/api/docs |

**Admin login** (за замовчуванням): `admin` / `admin123` — змініть через `ADMIN_USERNAME` / `ADMIN_PASSWORD` у `.env`.

**Кеш/коди**: SQLite у `database/kv.db`.

**База даних**: SQLite у `database/autoradar.db`.

**Bot ↔ Backend**: `INTERNAL_API_SECRET` у кореневому `.env` має бути однаковим для обох сервісів.

## Docker (production)

Повна інструкція для сервера: **[DOCKER.md](./DOCKER.md)**

```bash
cp .env.example .env   # налаштуйте production-змінні
mkdir -p database
docker compose up -d --build
```

## API модулі (`/api/v1/`)
- `auth`, `users`, `searches`, `listings`, `favorites`, `notifications`, `billing`, `telegram`
- `admin` — адмін-панель
- `internal/bot` — внутрішній API для Telegram-бота
