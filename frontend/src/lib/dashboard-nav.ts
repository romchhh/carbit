import {
  IconSearch,
  IconHeart,
  IconBell,
  IconChart,
  IconCreditCard,
  IconGear,
} from "@/components/icons";

export type NavBadgeKey = "favorites" | "notifications";

export type DashboardNavItem = {
  href: string;
  icon: typeof IconSearch;
  label: string;
  shortLabel?: string;
  badgeKey?: NavBadgeKey;
  badgeAccent?: boolean;
};

export const primaryNav: DashboardNavItem[] = [
  { href: "/app/dashboard", icon: IconSearch, label: "Мої пошуки", shortLabel: "Пошук" },
  { href: "/app/favorites", icon: IconHeart, label: "Обране", shortLabel: "Обране", badgeKey: "favorites" },
  { href: "/app/notifications", icon: IconBell, label: "Сповіщення", shortLabel: "Алерти", badgeKey: "notifications", badgeAccent: true },
  { href: "/app/stats", icon: IconChart, label: "Статистика", shortLabel: "Стат." },
];

export const secondaryNav: DashboardNavItem[] = [
  { href: "/app/account", icon: IconGear, label: "Акаунт" },
  { href: "/app/billing", icon: IconCreditCard, label: "Підписка" },
];

export const mobileNav: DashboardNavItem[] = [
  ...primaryNav,
  { href: "/app/account", icon: IconGear, label: "Акаунт", shortLabel: "Профіль" },
];
