import aliasData from "@/lib/search-data/brand-model-aliases.json";
import { brandNameToIconSlug } from "@/lib/search-data/brand-icons";
import { BRANDS, getModelsForBrand } from "@/lib/search-data/brands-models";

const CYRILLIC_TO_LATIN: Record<string, string> = {
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "e",
  ж: "zh",
  з: "z",
  и: "i",
  й: "y",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "h",
  ц: "ts",
  ч: "ch",
  ш: "sh",
  щ: "shch",
  ъ: "",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya",
  і: "i",
  ї: "i",
  є: "e",
  ґ: "g",
};

/** Нормалізація для пошуку марки/моделі (UA/RU/latin). */
export function normalizeSearchKey(raw: string): string {
  let text = (raw || "")
    .trim()
    .toLowerCase()
    .replace(/[''ʼ`´]/g, "")
    .replace(/&/g, " and ")
    .replace(/ё/g, "е");

  // Кирилична «С-клас» = C-Class (С виглядає як C; трансліт С→s дав би S-Class).
  text = text.replace(
    /(^|[^a-z\u0400-\u04ff0-9])[сc][\s\-]*(class|klass|клас(?:с)?)(?![a-z\u0400-\u04ff0-9])/gi,
    "$1c class",
  );

  text = text.replace(/[a-z\u0400-\u04ff0-9]+/g, token => {
    if (/^[a-z0-9]+$/i.test(token)) return token;
    return token
      .split("")
      .map(ch => CYRILLIC_TO_LATIN[ch] ?? ch)
      .join("");
  });

  return text
    .replace(/[^a-z0-9]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

const SLUG_TO_BRAND = new Map<string, string>();
for (const brand of BRANDS) {
  SLUG_TO_BRAND.set(brandNameToIconSlug(brand), brand);
}

function slugToBrandLabel(slug: string): string {
  const mapped = SLUG_TO_BRAND.get(slug);
  if (mapped) return mapped;
  return slug
    .split("-")
    .map(part => (part ? part.charAt(0).toUpperCase() + part.slice(1) : part))
    .join(" ");
}

const BRAND_ALIAS_TO_CANONICAL = new Map<string, string>();
for (const brand of BRANDS) {
  BRAND_ALIAS_TO_CANONICAL.set(normalizeSearchKey(brand), brand);
}
for (const [slug, aliases] of Object.entries(aliasData.brandSlugs)) {
  const canonical = SLUG_TO_BRAND.get(slug) ?? slugToBrandLabel(slug);
  if (!canonical) continue;
  BRAND_ALIAS_TO_CANONICAL.set(normalizeSearchKey(canonical), canonical);
  for (const alias of aliases) {
    BRAND_ALIAS_TO_CANONICAL.set(normalizeSearchKey(alias), canonical);
  }
}

const MODEL_ALIAS_TO_CANONICAL_BY_BRAND = new Map<string, Map<string, string>>();

function resolveModelAliasKey(brand: string, modelKey: string, models: string[]): string | null {
  const byNorm = new Map<string, string>();
  for (const model of models) {
    byNorm.set(normalizeSearchKey(model), model);
  }
  const normalizedKey = normalizeSearchKey(modelKey);
  const direct = byNorm.get(normalizedKey);
  if (direct) return direct;

  const brandPrefix = `${normalizeSearchKey(brand)} `;
  if (normalizedKey.startsWith(brandPrefix)) {
    const rest = normalizedKey.slice(brandPrefix.length);
    const fromPrefix = byNorm.get(rest);
    if (fromPrefix) return fromPrefix;
  }
  return null;
}

function modelIndexForBrand(brand: string): Map<string, string> {
  const cached = MODEL_ALIAS_TO_CANONICAL_BY_BRAND.get(brand);
  if (cached) return cached;

  const index = new Map<string, string>();
  const models = getModelsForBrand(brand);
  const byNorm = new Map<string, string>();

  for (const model of models) {
    const norm = normalizeSearchKey(model);
    index.set(norm, model);
    byNorm.set(norm, model);
  }

  for (const [modelKey, aliases] of Object.entries(aliasData.models)) {
    const canonical = resolveModelAliasKey(brand, modelKey, models);
    if (!canonical) continue;
    index.set(normalizeSearchKey(modelKey), canonical);
    for (const alias of aliases) {
      index.set(normalizeSearchKey(alias), canonical);
    }
  }

  MODEL_ALIAS_TO_CANONICAL_BY_BRAND.set(brand, index);
  return index;
}

function matchScore(aliasKey: string, queryKey: string): number {
  if (aliasKey === queryKey) return 0;
  if (aliasKey.startsWith(queryKey)) return 1;
  if (aliasKey.includes(queryKey)) return 2;
  return 99;
}

function rankMatches(
  queryKey: string,
  entries: Iterable<[string, string]>,
  allowed: Set<string>,
): string[] {
  const scores = new Map<string, number>();
  for (const [aliasKey, canonical] of entries) {
    if (!allowed.has(canonical)) continue;
    const score = matchScore(aliasKey, queryKey);
    if (score === 99) continue;
    const prev = scores.get(canonical);
    if (prev === undefined || score < prev) scores.set(canonical, score);
  }
  return [...scores.entries()]
    .sort((a, b) => a[1] - b[1] || a[0].localeCompare(b[0], "uk"))
    .map(([canonical]) => canonical);
}

export function filterBrandOptions(
  options: readonly string[],
  query: string,
  limit = 100,
): string[] {
  const key = normalizeSearchKey(query);
  if (!key) return options.slice(0, limit);
  const allowed = new Set(options);
  return rankMatches(key, BRAND_ALIAS_TO_CANONICAL, allowed).slice(0, limit);
}

export function resolveBrandQuery(query: string, options: readonly string[]): string | null {
  const key = normalizeSearchKey(query);
  if (!key) return null;
  const allowed = new Set(options);
  const exact = BRAND_ALIAS_TO_CANONICAL.get(key);
  if (exact && allowed.has(exact)) return exact;
  const ranked = filterBrandOptions(options, query, 2);
  return ranked.length === 1 ? ranked[0] : null;
}

export function filterModelOptions(
  brand: string,
  options: readonly string[],
  query: string,
  limit = 100,
): string[] {
  const key = normalizeSearchKey(query);
  if (!key) return options.slice(0, limit);
  const allowed = new Set(options);
  const index = modelIndexForBrand(brand);
  return rankMatches(key, index, allowed).slice(0, limit);
}

export function resolveModelQuery(
  brand: string,
  query: string,
  options: readonly string[],
): string | null {
  const key = normalizeSearchKey(query);
  if (!key || !brand) return null;
  const allowed = new Set(options);
  const index = modelIndexForBrand(brand);
  const exact = index.get(key);
  if (exact && allowed.has(exact)) return exact;
  const ranked = filterModelOptions(brand, options, query, 2);
  return ranked.length === 1 ? ranked[0] : null;
}

/** Шукає марку в довгому тексті диктовки (alias ⊆ haystack). */
export function findBrandInText(text: string, options: readonly string[]): string | null {
  const haystack = normalizeSearchKey(text);
  if (!haystack) return null;
  const allowed = new Set(options);
  let best: string | null = null;
  let bestLen = 0;
  for (const [aliasKey, canonical] of BRAND_ALIAS_TO_CANONICAL) {
    if (!allowed.has(canonical)) continue;
    if (haystack.includes(aliasKey) && aliasKey.length > bestLen) {
      best = canonical;
      bestLen = aliasKey.length;
    }
  }
  return best;
}

/** Шукає модель у тексті диктовки для обраної марки. */
export function findModelInText(
  brand: string,
  text: string,
  options: readonly string[],
): string | null {
  const haystack = normalizeSearchKey(text);
  if (!haystack || !brand) return null;
  const allowed = new Set(options);
  const index = modelIndexForBrand(brand);
  let best: string | null = null;
  let bestLen = 0;
  for (const [aliasKey, canonical] of index) {
    if (!allowed.has(canonical)) continue;
    if (haystack.includes(aliasKey) && aliasKey.length > bestLen) {
      best = canonical;
      bestLen = aliasKey.length;
    }
  }
  return best;
}
