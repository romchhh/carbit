import {
  IconSearch,
  IconHeart,
  IconBell,
  IconCreditCard,
  IconGear,
  IconZap,
} from "@/components/icons";

export type NavBadgeKey = "favorites" | "notifications" | "monitors";

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
    icon: IconZap,
    label: "Мої моніторинги",
    shortLabel: "Монітори",
    badgeKey: "monitors",
    badgeAccent: true,
    tourId: "nav-monitors",
  },
  { href: "/app/favorites", icon: IconHeart, label: "Обране", shortLabel: "Обране", badgeKey: "favorites", tourId: "nav-favorites" },
  { href: "/app/notifications", icon: IconBell, label: "Сповіщення", shortLabel: "Алерти", badgeKey: "notifications", badgeAccent: true, tourId: "nav-notifications" },
];

export const secondaryNav: DashboardNavItem[] = [
  { href: "/app/account", icon: IconGear, label: "Акаунт", tourId: "nav-account" },
  { href: "/app/billing", icon: IconCreditCard, label: "Підписка", tourId: "nav-billing" },
];

/** Bottom bar: без статистики, щоб лишилось місце під «Монітори». */
export const mobileNav: DashboardNavItem[] = [
  primaryNav[0],
  primaryNav[1],
  primaryNav[2],
  primaryNav[3],
  { href: "/app/account", icon: IconGear, label: "Акаунт", shortLabel: "Профіль" },
];
