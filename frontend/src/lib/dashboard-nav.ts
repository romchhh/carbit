import {
  IconSearch,
  IconHeart,
  IconBell,
  IconCreditCard,
  IconUser,
  IconCar,
  IconGlobe,
  IconCompare,
} from "@/components/icons";

export type NavBadgeKey = "notifications" | "monitors";

export type DashboardNavItem = {
  href: string;
  icon: typeof IconSearch;
  label: string;
  shortLabel?: string;
  badgeKey?: NavBadgeKey;
  badgeAccent?: boolean;
  tourId?: string;
};

export const primaryNav: DashboardNavItem[] = [
  { href: "/app/dashboard", icon: IconSearch, label: "Пошук", shortLabel: "Пошук", tourId: "nav-dashboard" },
  {
    href: "/app/monitors",
    icon: IconCar,
    label: "Мої моніторинги",
    shortLabel: "Монітори",
    badgeKey: "monitors",
    badgeAccent: true,
    tourId: "nav-monitors",
  },
  { href: "/app/favorites", icon: IconHeart, label: "Обране", shortLabel: "Обране", tourId: "nav-favorites" },
  { href: "/app/notifications", icon: IconBell, label: "Сповіщення", shortLabel: "Алерти", badgeKey: "notifications", badgeAccent: true, tourId: "nav-notifications" },
];

export const secondaryNav: DashboardNavItem[] = [
  { href: "/app/account", icon: IconUser, label: "Акаунт", tourId: "nav-account" },
  { href: "/app/billing", icon: IconCreditCard, label: "Підписка", tourId: "nav-billing" },
  { href: "/app/compare", icon: IconCompare, label: "Порівняння", tourId: "nav-compare" },
  { href: "/app/suggest-source", icon: IconGlobe, label: "Запропонувати джерело", tourId: "nav-suggest-source" },
];

/** Bottom bar: без статистики, щоб лишилось місце під «Монітори». */
export const mobileNav: DashboardNavItem[] = [
  primaryNav[0],
  primaryNav[1],
  primaryNav[2],
  primaryNav[3],
  { href: "/app/account", icon: IconUser, label: "Акаунт", shortLabel: "Профіль" },
];
