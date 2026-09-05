# syntax=docker/dockerfile:1

# Спільний шар pip — кешується між backend / worker / bot (поки не змінився requirements.txt).
FROM python:3.13-slim AS python-deps

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install -r requirements.txt \
    && python -c "from curl_cffi.requests import AsyncSession; print('curl_cffi OK')"

# Лише для backend (VIN / Playwright). Worker/bot цей stage не збирають.
FROM python-deps AS python-playwright

ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
    --mount=type=cache,target=/var/lib/apt/lists,sharing=locked \
    apt-get update \
    && apt-get install -y --no-install-recommends \
         libnss3 \
         libnspr4 \
         libatk1.0-0 \
         libatk-bridge2.0-0 \
         libcups2 \
         libdrm2 \
         libdbus-1-3 \
         libxcb1 \
         libx11-6 \
         libxcomposite1 \
         libxdamage1 \
         libxext6 \
         libxfixes3 \
         libxrandr2 \
         libgbm1 \
         libasound2 \
         libpango-1.0-0 \
         libcairo2 \
         libxkbcommon0 \
         fonts-liberation \
    && playwright install chromium \
    && rm -rf /tmp/*

# Код застосунку — окремий stage, щоб зміна .py не чіпала pip/playwright.
FROM python-deps AS app-tree

ENV PYTHONPATH=/app/backend:/app

COPY backend ./backend
COPY frontend/src/lib/search-data/brands-models.ts ./frontend/src/lib/search-data/brands-models.ts
COPY frontend/src/lib/search-data/brand-model-aliases.json ./frontend/src/lib/search-data/brand-model-aliases.json
COPY bot ./bot
COPY worker ./worker
COPY telegram_worker ./telegram_worker
COPY parser ./parser
COPY storage ./storage
COPY auth.py ./auth.py
COPY docker/python/entrypoint-backend.sh /entrypoint-backend.sh

RUN chmod +x /entrypoint-backend.sh \
    && mkdir -p /app/database

# Worker, bot, telegram-worker — без Chromium (~швидший rebuild).
FROM python-deps AS runtime-slim

ENV PYTHONPATH=/app/backend:/app

COPY --from=app-tree /app /app
COPY --from=app-tree /entrypoint-backend.sh /entrypoint-backend.sh

WORKDIR /app
EXPOSE 8000

# Backend — з Chromium.
FROM python-playwright AS runtime-playwright

ENV PYTHONPATH=/app/backend:/app \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

COPY --from=app-tree /app /app
COPY --from=app-tree /entrypoint-backend.sh /entrypoint-backend.sh

WORKDIR /app
EXPOSE 8000

ENTRYPOINT ["/entrypoint-backend.sh"]
