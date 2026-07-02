const path = require("path");
const { loadEnvConfig } = require("@next/env");

// Єдиний .env у корені монорепо
const rootDir = path.join(__dirname, "..");
loadEnvConfig(rootDir);

// Frontend читає TELEGRAM_BOT_* з кореневого .env (без дублювання NEXT_PUBLIC_*)
const telegramBotUsername =
  process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME?.trim() ||
  process.env.TELEGRAM_BOT_USERNAME?.trim() ||
  "";
const telegramBotUrl =
  process.env.NEXT_PUBLIC_TELEGRAM_BOT_URL?.trim() ||
  process.env.TELEGRAM_BOT_URL?.trim() ||
  "";

function isInternalBackendUrl(url) {
  return /:\/\/backend(?::|\/|$)/i.test(url) || /^backend:/i.test(url);
}

const apiUrl = (() => {
  const fromEnv = process.env.NEXT_PUBLIC_API_URL?.trim();
  if (fromEnv && !isInternalBackendUrl(fromEnv)) return fromEnv;
  if (process.env.NODE_ENV === "production") return "/api/v1";
  return "http://localhost:8000/api/v1";
})();

const backendInternal =
  process.env.BACKEND_INTERNAL_URL?.trim() ||
  (process.env.NODE_ENV === "production" ? "http://backend:8000" : "http://localhost:8000");

/** @type {import('next').NextConfig} */
const withPWA = require("next-pwa")({
  dest: "public",
  register: true,
  skipWaiting: true,
  disable: process.env.NODE_ENV === "development",
  // Не підміняти HTML на "/" — ламає client-side перехід у /app/* (помилка до F5).
  dynamicStartUrl: false,
  workboxOptions: {
    navigateFallback: null,
    navigateFallbackDenylist: [/^\/api\//, /^\/auth\//, /^\/admin/],
  },
});

const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: apiUrl,
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: telegramBotUsername,
    NEXT_PUBLIC_TELEGRAM_BOT_URL: telegramBotUrl,
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${backendInternal}/api/v1/:path*`,
      },
    ];
  },
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
    ],
  },
};

module.exports = withPWA(nextConfig);
