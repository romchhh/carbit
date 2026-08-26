import type { Listing } from "@/types/api";
import type { SearchFilterState } from "@/lib/search-catalog";
import { DEFAULT_FILTERS } from "@/lib/search-catalog";

export type LandingSamplePreset = {
  id: string;
  title: string;
  subtitle: string;
  filters: SearchFilterState;
  listing: Listing;
};

const now = new Date().toISOString();

function sampleListing(
  partial: Pick<Listing, "id" | "title" | "brand" | "model" | "year" | "price" | "mileage" | "fuel" | "region" | "images"> &
    Partial<Listing>,
): Listing {
  return {
    id: partial.id,
    source: partial.source ?? "auto_ria",
    title: partial.title,
    brand: partial.brand,
    model: partial.model,
    year: partial.year,
    price: partial.price,
    currency: partial.currency ?? "USD",
    mileage: partial.mileage,
    fuel: partial.fuel,
    transmission: partial.transmission ?? "automatic",
    region: partial.region,
    images: partial.images,
    url: partial.url ?? "#",
    seller_type: partial.seller_type ?? "private",
    price_history: [],
    is_duplicate: false,
    published_at: partial.published_at ?? now,
    found_at: partial.found_at ?? now,
  };
}

export const LANDING_SAMPLE_PRESETS: LandingSamplePreset[] = [
  {
    id: "toyota-camry",
    title: "Toyota Camry",
    subtitle: "Седани · до $18 000 · Київ",
    filters: {
      ...DEFAULT_FILTERS,
      region: "Київ",
      regions: ["Київ"],
      currency: "USD",
      brand: "Toyota",
      model: "Camry",
      priceTo: "18000",
      yearFrom: "2016",
    },
    listing: sampleListing({
      id: "sample-camry",
      title: "Toyota Camry 2.5 Hybrid",
      brand: "Toyota",
      model: "Camry",
      year: 2019,
      price: 16900,
      mileage: 87000,
      fuel: "Гібрид",
      region: "Київ",
      images: [
        "https://images.unsplash.com/photo-1621007947382-bb3c3994e3fb?auto=format&fit=crop&w=800&q=80",
      ],
    }),
  },
  {
    id: "vw-golf",
    title: "Volkswagen Golf",
    subtitle: "Хетчбек · до $12 000 · Львів",
    filters: {
      ...DEFAULT_FILTERS,
      region: "Львів",
      regions: ["Львів"],
      currency: "USD",
      brand: "Volkswagen",
      model: "Golf",
      priceTo: "12000",
      yearFrom: "2015",
    },
    listing: sampleListing({
      id: "sample-golf",
      title: "Volkswagen Golf 1.4 TSI",
      brand: "Volkswagen",
      model: "Golf",
      year: 2017,
      price: 10900,
      mileage: 112000,
      fuel: "Бензин",
      region: "Львів",
      images: [
        "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=800&q=80",
      ],
    }),
  },
  {
    id: "bmw-x5",
    title: "BMW X5",
    subtitle: "Кросовер · дизель · Одеса",
    filters: {
      ...DEFAULT_FILTERS,
      region: "Одеса",
      regions: ["Одеса"],
      currency: "USD",
      brand: "BMW",
      model: "X5",
      fuels: ["Дизель"],
      yearFrom: "2014",
      priceTo: "25000",
    },
    listing: sampleListing({
      id: "sample-x5",
      title: "BMW X5 xDrive30d",
      brand: "BMW",
      model: "X5",
      year: 2016,
      price: 23500,
      mileage: 145000,
      fuel: "Дизель",
      region: "Одеса",
      images: [
        "https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=800&q=80",
      ],
    }),
  },
];
