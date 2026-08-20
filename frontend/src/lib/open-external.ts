/**
 * Відкриває зовнішнє посилання в новій вкладці.
 * Не замінює поточну сторінку Carbit (щоб не губився пошук).
 */
export function openExternalUrl(url: string, event?: { preventDefault?: () => void; stopPropagation?: () => void }) {
  event?.preventDefault?.();
  event?.stopPropagation?.();
  if (!url) return;
  const opened = window.open(url, "_blank", "noopener,noreferrer");
  if (opened) {
    opened.opener = null;
    return;
  }
  // Fallback якщо браузер заблокував popup — все одно нова вкладка через <a>.
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.target = "_blank";
  anchor.rel = "noopener noreferrer";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
}
