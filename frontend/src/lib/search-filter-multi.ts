import { getModelsForBrand } from "@/lib/search-data/brands-models";
import type { SearchFilterState } from "@/lib/search-catalog";
import { toggleValue } from "@/lib/search-catalog";

const ALL_UKRAINE = "Вся Україна";

export function effectiveBrands(filters: SearchFilterState): string[] {
  if (filters.brands.length) return [...filters.brands];
  return filters.brand ? [filters.brand] : [];
}

export function effectiveModels(filters: SearchFilterState): string[] {
  if (filters.models.length) return [...filters.models];
  return filters.model ? [filters.model] : [];
}

export function effectiveRegions(filters: SearchFilterState): string[] {
  if (filters.regions.length) return [...filters.regions];
  const region = filters.region?.trim();
  if (!region || region === ALL_UKRAINE || region === "Всі регіони") return [];
  return [region];
}

/** Синхронізує масиви з legacy полями brand/model/region. */
export function syncSearchFilterArrays(filters: SearchFilterState): SearchFilterState {
  const brands = effectiveBrands(filters);
  const models = effectiveModels(filters);
  const regions = effectiveRegions(filters);

  return {
    ...filters,
    brands,
    models,
    regions,
    brand: brands[0] ?? "",
    model: models[0] ?? "",
    region: regions.length === 1 ? regions[0] : regions.length ? "" : ALL_UKRAINE,
  };
}

export function getModelsForBrands(brands: string[]): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const brand of brands) {
    for (const model of getModelsForBrand(brand)) {
      if (!seen.has(model)) {
        seen.add(model);
        out.push(model);
      }
    }
  }
  return out;
}

export function toggleBrand(filters: SearchFilterState, brand: string): SearchFilterState {
  const brands = toggleValue(effectiveBrands(filters), brand);
  const models = effectiveModels(filters).filter(model =>
    brands.some(b => getModelsForBrand(b).includes(model)),
  );
  return syncSearchFilterArrays({ ...filters, brands, models });
}

export function toggleModel(filters: SearchFilterState, model: string): SearchFilterState {
  const models = toggleValue(effectiveModels(filters), model);
  return syncSearchFilterArrays({ ...filters, models });
}

export function toggleRegion(filters: SearchFilterState, region: string): SearchFilterState {
  const regions = toggleValue(effectiveRegions(filters), region);
  return syncSearchFilterArrays({ ...filters, regions });
}

export function clearBrands(filters: SearchFilterState): SearchFilterState {
  return syncSearchFilterArrays({ ...filters, brands: [], models: [], brand: "", model: "" });
}

export function clearModels(filters: SearchFilterState): SearchFilterState {
  return syncSearchFilterArrays({ ...filters, models: [], model: "" });
}

export function clearRegions(filters: SearchFilterState): SearchFilterState {
  return syncSearchFilterArrays({ ...filters, regions: [], region: ALL_UKRAINE });
}

export function formatMultiSelectionLabel(
  values: string[],
  emptyLabel: string,
  singularLabel?: string,
): string {
  if (values.length === 0) return emptyLabel;
  if (values.length === 1) return singularLabel ?? values[0];
  if (values.length === 2) return values.join(", ");
  return `${values.length} обрано`;
}
