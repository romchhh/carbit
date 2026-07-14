import type { User } from "@/types/api";

const ONBOARDING_KEY = "autoradar_onboarding_done";
const PENDING_KEY = "autoradar_show_onboarding";
const FORCE_TOUR_KEY = "autoradar_force_tour";
export const ONBOARDING_TOUR_EVENT = "carbit:start-tour";

export function shouldShowOnboarding(user?: User | null): boolean {
  if (typeof window === "undefined") return false;
  if (sessionStorage.getItem(FORCE_TOUR_KEY) === "true") return true;
  if (user?.onboarding_completed) return false;
  if (localStorage.getItem(ONBOARDING_KEY) === "true") return false;
  return sessionStorage.getItem(PENDING_KEY) === "true";
}

export function markOnboardingPending(): void {
  sessionStorage.setItem(PENDING_KEY, "true");
}

export function requestOnboardingTour(): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(FORCE_TOUR_KEY, "true");
  window.dispatchEvent(new Event(ONBOARDING_TOUR_EVENT));
}

export function completeOnboarding(): void {
  localStorage.setItem(ONBOARDING_KEY, "true");
  sessionStorage.removeItem(PENDING_KEY);
  sessionStorage.removeItem(FORCE_TOUR_KEY);
}
