import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPrice(price: number, currency = "грн") {
  return new Intl.NumberFormat("uk-UA").format(price) + " " + currency;
}

export function formatMileage(km: number) {
  return new Intl.NumberFormat("uk-UA").format(km) + " км";
}

export function getInitials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

const AVATAR_COLORS = [
  "bg-emerald text-white",
  "bg-ink text-white",
  "bg-[#229ED9] text-white",
  "bg-violet-600 text-white",
  "bg-amber-600 text-white",
  "bg-rose-600 text-white",
  "bg-teal-600 text-white",
  "bg-indigo-600 text-white",
];

export function avatarColorClass(name: string): string {
  let hash = 0;
  for (const char of name.trim()) {
    hash = (hash + char.charCodeAt(0)) % AVATAR_COLORS.length;
  }
  return AVATAR_COLORS[hash];
}

export const PLAN_LABELS: Record<string, string> = {
  free: "Безкоштовний",
  lite: "Лайт",
  standard: "Стандарт",
  pro: "Про",
};

export function timeAgo(date: string) {
  const diff = Date.now() - new Date(date).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 60) return `${mins} хв тому`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} год тому`;
  return `${Math.floor(hours / 24)} дн тому`;
}
