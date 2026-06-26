# syntax=docker/dockerfile:1

FROM node:20-alpine AS deps
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/frontend/node_modules ./frontend/node_modules
COPY frontend ./frontend

ARG BACKEND_URL=http://localhost:8000/api/v1
ARG BACKEND_INTERNAL_URL=http://backend:8000
ARG TELEGRAM_BOT_USERNAME=
ARG TELEGRAM_BOT_URL=

ENV NEXT_TELEMETRY_DISABLED=1 \
    NODE_ENV=production \
    BACKEND_URL=$BACKEND_URL \
    BACKEND_INTERNAL_URL=$BACKEND_INTERNAL_URL \
    TELEGRAM_BOT_USERNAME=$TELEGRAM_BOT_USERNAME \
    TELEGRAM_BOT_URL=$TELEGRAM_BOT_URL

WORKDIR /app/frontend
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/frontend/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/frontend/.next/static ./.next/static

USER nextjs
EXPOSE 3000

CMD ["node", "server.js"]
