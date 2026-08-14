FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "from curl_cffi.requests import AsyncSession; print('curl_cffi OK')" \
    && playwright install --with-deps chromium

COPY backend ./backend
COPY frontend/src/lib/search-data/brands-models.ts ./frontend/src/lib/search-data/brands-models.ts
COPY frontend/src/lib/search-data/brand-model-aliases.json ./frontend/src/lib/search-data/brand-model-aliases.json
COPY bot ./bot
COPY support_bot ./support_bot
COPY worker ./worker
COPY telegram_worker ./telegram_worker
COPY parser ./parser
COPY storage ./storage
COPY auth.py ./auth.py
COPY docker/python/entrypoint-backend.sh /entrypoint-backend.sh

RUN chmod +x /entrypoint-backend.sh \
    && mkdir -p /app/database

EXPOSE 8000

ENTRYPOINT ["/entrypoint-backend.sh"]
