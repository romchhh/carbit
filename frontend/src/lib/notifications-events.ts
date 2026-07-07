export const NOTIFICATIONS_CHANGED_EVENT = "carbit:notifications-changed";

export function notifyNotificationsChanged() {
  window.dispatchEvent(new CustomEvent(NOTIFICATIONS_CHANGED_EVENT));
}
