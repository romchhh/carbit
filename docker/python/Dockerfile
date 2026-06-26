FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/backend:/app

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend ./backend
COPY bot ./bot
COPY storage ./storage
COPY docker/python/entrypoint-backend.sh /entrypoint-backend.sh

RUN chmod +x /entrypoint-backend.sh \
    && mkdir -p /app/database

EXPOSE 8000

ENTRYPOINT ["/entrypoint-backend.sh"]
