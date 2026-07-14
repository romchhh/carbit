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

const defaultCache = require("next-pwa/cache");

// Без кешування HTML/RSC — інакше на телефоні «через раз» кнопки та падіння Next.js.
const runtimeCaching = [
  ...defaultCache.filter(entry => {
    const cacheName = entry.options?.cacheName;
    return cacheName !== "others" && cacheName !== "next-data";
  }),
  {
    urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
    handler: "NetworkOnly",
    method: "GET",
  },
  {
    urlPattern: ({ url }) => url.pathname.startsWith("/api/"),
    handler: "NetworkOnly",
    method: "POST",
  },
  {
    urlPattern: /\/_next\/data\/.+\/.+\.json$/i,
    handler: "NetworkOnly",
  },
  {
    urlPattern: ({ request }) => request.destination === "document",
    handler: "NetworkOnly",
  },
];

/** @type {import('next').NextConfig} */
const withPWA = require("next-pwa")({
  dest: "public",
  register: false,
  skipWaiting: true,
  clientsClaim: true,
  cleanupOutdatedCaches: true,
  cacheStartUrl: false,
  cacheOnFrontEndNav: false,
  reloadOnOnline: false,
  disable: process.env.NODE_ENV === "development",
  dynamicStartUrl: false,
  navigateFallback: null,
  navigateFallbackDenylist: [/^\/api\//, /^\/auth\//, /^\/admin/, /^\/app\//],
  runtimeCaching,
});

// Absolute API URL → браузер б'є backend напряму (CORS). Relative `/api/v1` → Route Handler proxy.
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  env: {
    NEXT_PUBLIC_API_URL: apiUrl,
    NEXT_PUBLIC_TELEGRAM_BOT_USERNAME: telegramBotUsername,
    NEXT_PUBLIC_TELEGRAM_BOT_URL: telegramBotUrl,
  },
  // Cookie-aware proxy: src/app/api/v1/[...path]/route.ts
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "**" },
    ],
  },
};

module.exports = withPWA(nextConfig);
