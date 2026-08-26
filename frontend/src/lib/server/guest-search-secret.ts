/** Спільний секрет для підпису guest-cookie та proxy → backend (має збігатися з INTERNAL_API_SECRET). */
export function getGuestSearchInternalSecret(): string {
  const fromEnv = process.env.INTERNAL_API_SECRET?.trim();
  if (fromEnv) return fromEnv;

  // Локальний dev без docker: у .env часто немає INTERNAL_API_SECRET для frontend
  if (process.env.NODE_ENV !== "production") {
    return "change-me-internal";
  }

  return "";
}
