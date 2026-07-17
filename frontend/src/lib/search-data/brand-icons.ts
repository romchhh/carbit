/** Мапінг марок FE → файли в /public/brands (svg або png). */

const BRAND_ICON_EXT: Record<string, "svg" | "png"> = {
  chevrolet: "png",
  ford: "png",
  honda: "png",
  mg: "png",
  polestar: "png",
  subaru: "png",
};

/** Slug-и з наявними файлами в public/brands */
const BRAND_ICON_SLUGS = new Set([
  "audi",
  "bmw",
  "byd",
  "chevrolet",
  "citroen",
  "daf",
  "ducati",
  "fiat",
  "ford",
  "harley-davidson",
  "honda",
  "hyundai",
  "indian",
  "iveco",
  "jeep",
  "kawasaki",
  "kia",
  "ktm",
  "land-rover",
  "lexus",
  "man",
  "mazda",
  "mercedes-benz",
  "mg",
  "mitsubishi",
  "nissan",
  "opel",
  "peugeot",
  "polestar",
  "porsche",
  "renault",
  "renault-trucks",
  "scania",
  "skoda",
  "subaru",
  "suzuki",
  "tesla",
  "toyota",
  "triumph",
  "volkswagen",
  "volvo",
  "yamaha",
]);

export function brandNameToIconSlug(brand: string): string {
  return brand
    .trim()
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

/** URL іконки марки або null, якщо файлу немає в public/brands. */
export function getBrandIconUrl(brand: string): string | null {
  if (!brand.trim()) return null;
  const slug = brandNameToIconSlug(brand);
  if (!BRAND_ICON_SLUGS.has(slug)) return null;
  const ext = BRAND_ICON_EXT[slug] ?? "svg";
  return `/brands/${slug}.${ext}`;
}

export function hasBrandIcon(brand: string): boolean {
  return BRAND_ICON_SLUGS.has(brandNameToIconSlug(brand));
}
