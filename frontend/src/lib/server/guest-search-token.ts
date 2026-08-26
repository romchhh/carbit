import { createHmac, randomBytes, timingSafeEqual } from "crypto";

export const GUEST_SEARCH_COOKIE = "carbit_gs";
const TTL_SEC = 60 * 60;

export function issueGuestSearchToken(secret: string): string {
  const exp = Math.floor(Date.now() / 1000) + TTL_SEC;
  const nonce = randomBytes(12).toString("base64url");
  const payload = `${exp}.${nonce}`;
  const sig = createHmac("sha256", secret).update(payload).digest("base64url");
  return `${payload}.${sig}`;
}

export function verifyGuestSearchToken(secret: string, token: string | undefined): boolean {
  if (!token || !secret) return false;
  const parts = token.split(".");
  if (parts.length !== 3) return false;
  const [expStr, nonce, sig] = parts;
  const exp = Number(expStr);
  if (!Number.isFinite(exp) || exp < Math.floor(Date.now() / 1000)) return false;
  const payload = `${expStr}.${nonce}`;
  const expected = createHmac("sha256", secret).update(payload).digest("base64url");
  try {
    const a = Buffer.from(sig);
    const b = Buffer.from(expected);
    return a.length === b.length && timingSafeEqual(a, b);
  } catch {
    return false;
  }
}

export function guestSearchCookieOptions(secure: boolean) {
  return {
    httpOnly: true,
    sameSite: "lax" as const,
    secure,
    path: "/",
    maxAge: TTL_SEC,
  };
}
