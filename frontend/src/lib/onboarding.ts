const ONBOARDING_KEY = "autoradar_onboarding_done";

export function shouldShowOnboarding(): boolean {
  if (typeof window === "undefined") return false;
  return sessionStorage.getItem("autoradar_show_onboarding") === "true"
    && localStorage.getItem(ONBOARDING_KEY) !== "true";
}

export function markOnboardingPending(): void {
  sessionStorage.setItem("autoradar_show_onboarding", "true");
}

export function completeOnboarding(): void {
  localStorage.setItem(ONBOARDING_KEY, "true");
  sessionStorage.removeItem("autoradar_show_onboarding");
}
