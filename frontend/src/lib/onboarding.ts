import type { User } from "@/types/api";

const ONBOARDING_KEY = "autoradar_onboarding_done";

export function shouldShowOnboarding(user?: User | null): boolean {
  if (typeof window === "undefined") return false;
  if (user?.onboarding_completed) return false;
  if (localStorage.getItem(ONBOARDING_KEY) === "true") return false;
  return sessionStorage.getItem("autoradar_show_onboarding") === "true";
}

export function markOnboardingPending(): void {
  sessionStorage.setItem("autoradar_show_onboarding", "true");
}

export function completeOnboarding(): void {
  localStorage.setItem(ONBOARDING_KEY, "true");
  sessionStorage.removeItem("autoradar_show_onboarding");
}
