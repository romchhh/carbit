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
  tourId?: string;
};

export const primaryNav: DashboardNavItem[] = [
  { href: "/app/dashboard", icon: IconSearch, label: "Мої пошуки", shortLabel: "Пошук", tourId: "nav-dashboard" },
  { href: "/app/favorites", icon: IconHeart, label: "Обране", shortLabel: "Обране", badgeKey: "favorites", tourId: "nav-favorites" },
  { href: "/app/notifications", icon: IconBell, label: "Сповіщення", shortLabel: "Алерти", badgeKey: "notifications", badgeAccent: true, tourId: "nav-notifications" },
  { href: "/app/stats", icon: IconChart, label: "Статистика", shortLabel: "Стат.", tourId: "nav-stats" },
];

export const secondaryNav: DashboardNavItem[] = [
  { href: "/app/account", icon: IconGear, label: "Акаунт", tourId: "nav-account" },
  { href: "/app/billing", icon: IconCreditCard, label: "Підписка", tourId: "nav-billing" },
];

export const mobileNav: DashboardNavItem[] = [
  ...primaryNav,
  { href: "/app/account", icon: IconGear, label: "Акаунт", shortLabel: "Профіль" },
];
