function normalizeUsername(raw: string): string {
  return raw.trim().replace(/^@/, "");
}

/** @username з .env (TELEGRAM_BOT_USERNAME → next.config.js) */
export function getTelegramBotUsername(): string {
  return normalizeUsername(process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "");
}

/** Посилання t.me з .env (TELEGRAM_BOT_URL або username) */
export function getTelegramBotUrl(startParam?: string): string {
  const fromEnv = process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL?.trim().replace(/\/$/, "");
  const base =
    fromEnv ||
    (getTelegramBotUsername() ? `https://t.me/${getTelegramBotUsername()}` : "");

  if (!base) return "";
  if (!startParam) return base;

  const separator = base.includes("?") ? "&" : "?";
  return `${base}${separator}start=${encodeURIComponent(startParam)}`;
}

/** Відображення @BotName */
export function getTelegramBotMention(): string {
  const username = getTelegramBotUsername();
  return username ? `@${username}` : "";
}

export function isTelegramBotConfigured(): boolean {
  return Boolean(getTelegramBotUrl());
}

/** Окремий бот підтримки — фіксоване посилання */
export const TELEGRAM_SUPPORT_BOT_URL = "https://t.me/Carbit_Support_Bot";
export const TELEGRAM_SUPPORT_BOT_USERNAME = "Carbit_Support_Bot";

export function getTelegramSupportBotUsername(): string {
  return TELEGRAM_SUPPORT_BOT_USERNAME;
}

export function getTelegramSupportBotUrl(): string {
  return TELEGRAM_SUPPORT_BOT_URL;
}

export function getTelegramSupportBotMention(): string {
  return `@${TELEGRAM_SUPPORT_BOT_USERNAME}`;
}

export function isTelegramSupportBotConfigured(): boolean {
  return true;
}
