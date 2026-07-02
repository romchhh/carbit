const DEFAULT_DEV_API = "http://localhost:8000/api/v1";
const DEFAULT_PROD_API = "/api/v1";

function isInternalBackendUrl(url: string): boolean {
  return /:\/\/backend(?::|\/|$)/i.test(url) || /^backend:/i.test(url);
}

/** URL API для браузера та SSR. Ніколи не повертає Docker-internal host у клієнті. */
export function getApiUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_URL?.trim();

  if (typeof window !== "undefined") {
    if (!configured || isInternalBackendUrl(configured)) {
      return DEFAULT_PROD_API;
    }
    return configured;
  }

  if (configured && !isInternalBackendUrl(configured)) {
    return configured;
  }

  const internal = process.env.BACKEND_INTERNAL_URL?.trim();
  if (internal) {
    return `${internal.replace(/\/$/, "")}/api/v1`;
  }

  return process.env.NODE_ENV === "production" ? DEFAULT_PROD_API : DEFAULT_DEV_API;
}
