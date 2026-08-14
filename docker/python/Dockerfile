FROM python:3.13-slim

# 0 = bot/worker/telegram-worker (без Chromium)
# 1 = backend (VIN-аукціон через Playwright)
ARG INSTALL_PLAYWRIGHT=0

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -c "from curl_cffi.requests import AsyncSession; print('curl_cffi OK')" \
    && if [ "$INSTALL_PLAYWRIGHT" = "1" ]; then \
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
         && rm -rf /var/lib/apt/lists/* \
         && playwright install chromium \
         && rm -rf /tmp/* /root/.cache/pip; \
       else \
         echo "Playwright browser skipped (INSTALL_PLAYWRIGHT=$INSTALL_PLAYWRIGHT)"; \
       fi

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

EXPOSE 8000

ENTRYPOINT ["/entrypoint-backend.sh"]
