import { getModelsForBrand } from "@/lib/search-data/brands-models";
import type { SearchFilterState } from "@/lib/search-catalog";

const ALL_UKRAINE = "Вся Україна";

export function effectiveBrands(filters: SearchFilterState): string[] {
  return syncSearchFilterArrays(filters).brands;
}

export function effectiveModels(filters: SearchFilterState): string[] {
  return syncSearchFilterArrays(filters).models;
}

export function effectiveRegions(filters: SearchFilterState): string[] {
  return syncSearchFilterArrays(filters).regions;
}

/** Лише одна марка / модель / регіон — синхронізуємо legacy поля з масивами. */
export function syncSearchFilterArrays(filters: SearchFilterState): SearchFilterState {
  const brand = (filters.brand || filters.brands[0] || "").trim();
  const model = (filters.model || filters.models[0] || "").trim();
  const regionRaw = (filters.region || filters.regions[0] || ALL_UKRAINE).trim();
  const region =
    !regionRaw || regionRaw === "Всі регіони" ? ALL_UKRAINE : regionRaw;

  const validModel =
    brand && model && getModelsForBrand(brand).includes(model) ? model : "";

  return {
    ...filters,
    brand,
    model: validModel,
    region,
    brands: brand ? [brand] : [],
    models: validModel ? [validModel] : [],
    regions: region === ALL_UKRAINE ? [] : [region],
  };
}
