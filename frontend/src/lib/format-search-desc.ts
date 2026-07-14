export function formatSearchDesc(filters: Record<string, unknown>): string {
  const parts: string[] = [];
  if (filters.brand) parts.push(String(filters.brand));
  if (filters.model) parts.push(String(filters.model));
  if (filters.year_from || filters.year_to) {
    parts.push(`${filters.year_from ?? "…"}–${filters.year_to ?? "…"}`);
  }
  if (filters.price_from || filters.price_to) {
    const from = filters.price_from ? Number(filters.price_from).toLocaleString("uk-UA") : "…";
    const to = filters.price_to ? Number(filters.price_to).toLocaleString("uk-UA") : "…";
    const currency =
      filters.currency === "USD" ? "$" : filters.currency === "EUR" ? "€" : "грн";
    parts.push(`${from}–${to} ${currency}`);
  }
  if (filters.region) parts.push(String(filters.region));
  return parts.length > 0 ? parts.join(" · ") : "Без фільтрів";
}
