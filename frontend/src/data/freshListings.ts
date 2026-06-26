export type FreshListing = {
  id: string;
  title: string;
  price: string;
  year: number;
  mileage: string;
  transmission: string;
  fuel: string;
  city: string;
  source: "Telegram" | "AUTO.RIA" | "OLX";
  image: string;
  isNew?: boolean;
  priceDown?: boolean;
};

const LISTING_COVER_IMAGE =
  "https://images.unsplash.com/photo-1618843479313-40f8afb4b4d8?auto=format&fit=crop&w=640&q=80";

export const FRESH_LISTINGS: FreshListing[] = [
  {
    id: "1",
    title: "Toyota Camry 2.5",
    price: "2 450 000 ₴",
    year: 2021,
    mileage: "45 000 км",
    transmission: "Автомат",
    fuel: "Бензин",
    city: "Київ",
    source: "Telegram",
    image: LISTING_COVER_IMAGE,
    isNew: true,
  },
  {
    id: "2",
    title: "BMW 5 серії",
    price: "3 890 000 ₴",
    year: 2020,
    mileage: "62 000 км",
    transmission: "Автомат",
    fuel: "Дизель",
    city: "Львів",
    source: "AUTO.RIA",
    image: LISTING_COVER_IMAGE,
    priceDown: true,
  },
  {
    id: "3",
    title: "Kia K5",
    price: "2 190 000 ₴",
    year: 2022,
    mileage: "28 000 км",
    transmission: "Автомат",
    fuel: "Бензин",
    city: "Одеса",
    source: "OLX",
    image: LISTING_COVER_IMAGE,
  },
  {
    id: "4",
    title: "Volkswagen Tiguan",
    price: "1 680 000 ₴",
    year: 2019,
    mileage: "89 000 км",
    transmission: "Автомат",
    fuel: "Бензин",
    city: "Дніпро",
    source: "AUTO.RIA",
    image: LISTING_COVER_IMAGE,
    isNew: true,
  },
  {
    id: "5",
    title: "Hyundai Tucson",
    price: "1 520 000 ₴",
    year: 2020,
    mileage: "71 000 км",
    transmission: "Автомат",
    fuel: "Дизель",
    city: "Харків",
    source: "OLX",
    image: LISTING_COVER_IMAGE,
    priceDown: true,
  },
  {
    id: "6",
    title: "Mercedes-Benz E 220",
    price: "4 350 000 ₴",
    year: 2019,
    mileage: "98 000 км",
    transmission: "Автомат",
    fuel: "Дизель",
    city: "Київ",
    source: "AUTO.RIA",
    image: LISTING_COVER_IMAGE,
  },
  {
    id: "7",
    title: "Skoda Octavia",
    price: "980 000 ₴",
    year: 2018,
    mileage: "112 000 км",
    transmission: "Механіка",
    fuel: "Бензин",
    city: "Вінниця",
    source: "Telegram",
    image: LISTING_COVER_IMAGE,
    isNew: true,
  },
  {
    id: "8",
    title: "Audi A6 3.0 TDI",
    price: "3 120 000 ₴",
    year: 2021,
    mileage: "54 000 км",
    transmission: "Автомат",
    fuel: "Дизель",
    city: "Запоріжжя",
    source: "AUTO.RIA",
    image: LISTING_COVER_IMAGE,
    priceDown: true,
  },
  {
    id: "9",
    title: "Honda CR-V",
    price: "1 890 000 ₴",
    year: 2020,
    mileage: "67 000 км",
    transmission: "Автомат",
    fuel: "Бензин",
    city: "Львів",
    source: "OLX",
    image: LISTING_COVER_IMAGE,
  },
  {
    id: "10",
    title: "Renault Duster",
    price: "720 000 ₴",
    year: 2017,
    mileage: "134 000 км",
    transmission: "Механіка",
    fuel: "Бензин",
    city: "Полтава",
    source: "Telegram",
    image: LISTING_COVER_IMAGE,
    isNew: true,
  },
];
