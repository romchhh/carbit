import type { Listing } from "@/types/api";

export type SellerContact = {
  name?: string | null;
  phone?: string | null;
  telegram?: string | null;
  url?: string | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : null;
}

function readString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
}

function isMaskedPhone(value: string): boolean {
  return /[xх*]{2,}|\.{3,}/i.test(value);
}

function normalizePhone(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.startsWith("380") && digits.length === 12) return `+${digits}`;
  if (digits.startsWith("0") && digits.length === 10) return `+38${digits}`;
  if (digits.length === 9) return `+380${digits}`;
  return value.trim();
}

function phoneFromText(text: string | null | undefined): string | null {
  if (!text) return null;
  const match = text.match(/(?:\+?38)?[\s\-()]*0\d{2}[\s\-()]*\d{3}[\s\-()]*\d{2}[\s\-()]*\d{2}/);
  if (!match) return null;
  const normalized = normalizePhone(match[0]);
  return isMaskedPhone(normalized) ? null : normalized;
}

function telegramFromText(text: string | null | undefined): string | null {
  if (!text) return null;
  const match = text.match(/(?:@|t\.me\/)([A-Za-z0-9_]{3,32})/i);
  return match?.[1] ?? null;
}

export function resolveSellerContact(listing: Listing): SellerContact | null {
  const sd = asRecord(listing.source_data);
  const imperiya = asRecord(sd?.imperiya);
  const udrive = asRecord(sd?.udrive);
  const dealer =
    asRecord(imperiya?.dealer) ??
    asRecord(udrive?.holderDealer) ??
    asRecord(udrive?.dealer) ??
    asRecord(sd?.dealer);
  const udriveContact = asRecord(dealer?.salesContact);

  const name =
    readString(listing.seller_name) ??
    readString(dealer?.name) ??
    readString(asRecord(imperiya?.contact)?.name) ??
    readString(udriveContact?.name);

  let phone =
    readString(listing.seller_phone) ??
    readString(sd?.phone) ??
    readString(udriveContact?.telephone);
  if (phone && isMaskedPhone(phone)) phone = null;
  if (!phone) phone = phoneFromText(listing.description);

  let telegram =
    readString(listing.seller_telegram) ?? readString(sd?.contact_username);
  if (!telegram) telegram = telegramFromText(listing.description);

  const url = readString(listing.seller_url) ?? readString(dealer?.link);

  if (!name && !phone && !telegram && !url) return null;

  return { name, phone, telegram, url };
}

export function formatPhoneDisplay(phone: string): string {
  const digits = phone.replace(/\D/g, "");
  if (digits.length === 12 && digits.startsWith("380")) {
    return `+38 (${digits.slice(2, 5)}) ${digits.slice(5, 8)}-${digits.slice(8, 10)}-${digits.slice(10)}`;
  }
  return phone;
}

export function sellerTelegramUrl(username: string): string {
  return `https://t.me/${username.replace(/^@/, "")}`;
}

export function hasSellerContact(listing: Listing): boolean {
  return resolveSellerContact(listing) != null;
}
