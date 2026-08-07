const DISMISS_KEY = "carbit_instagram_prompt_dismissed";
const FOLLOWED_KEY = "carbit_instagram_prompt_followed";
const SESSION_KEY = "carbit_instagram_prompt_shown_session";
const DISMISS_DAYS = 14;
/** Ймовірність показу при вході в кабінет (якщо не закривали недавно). */
const SHOW_PROBABILITY = 0.38;

function daysSince(ts: number) {
  return (Date.now() - ts) / (24 * 60 * 60 * 1000);
}

export function shouldShowInstagramFollowPrompt(): boolean {
  if (typeof window === "undefined") return false;
  if (localStorage.getItem(FOLLOWED_KEY) === "1") return false;
  if (sessionStorage.getItem(SESSION_KEY) === "1") return false;

  const dismissed = localStorage.getItem(DISMISS_KEY);
  if (dismissed) {
    const ts = Number(dismissed);
    if (!Number.isNaN(ts) && daysSince(ts) < DISMISS_DAYS) return false;
  }

  return Math.random() < SHOW_PROBABILITY;
}

export function markInstagramFollowPromptShown() {
  sessionStorage.setItem(SESSION_KEY, "1");
}

export function dismissInstagramFollowPrompt() {
  localStorage.setItem(DISMISS_KEY, String(Date.now()));
  markInstagramFollowPromptShown();
}

export function markInstagramFollowPromptFollowed() {
  localStorage.setItem(FOLLOWED_KEY, "1");
  markInstagramFollowPromptShown();
}
