/** Підзаголовок під назвою моніторингу: рік і ціна (без дубля brand/model/region). */
export function formatSearchDesc(filters: Record<string, unknown>): string {
  const parts: string[] = [];
  const categoryLabels: Record<string, string> = {
    used: "Вживані",
    new: "Нові",
    import: "Під пригон",
  };
  if (filters.category && filters.category !== "all") {
    const label = categoryLabels[String(filters.category)];
    if (label) parts.push(label);
  }
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
  return parts.length > 0 ? parts.join(" · ") : "Без додаткових фільтрів";
}
