import type { Listing } from "@/types/api";

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? (value as Record<string, unknown>)
    : {};
}

const ACCIDENT_HAD =
  /(?:^|(?<![\wа-яіїєґ]))(?:дтп|accident|after crash|після дтп|був у дтп|був в дтп|after an accident)(?:$|(?![\wа-яіїєґ]))/i;
const ACCIDENT_NONE =
  /(?:^|(?<![\wа-яіїєґ]))(?:без дтп|не в дтп|не був у дтп|не був в дтп|дтп не був|дтп небув|в дтп не був|в дтп небув|no accident|not damaged|не бита|не бит)(?:$|(?![\wа-яіїєґ]))/i;

/** true — був у ДТП, false — не був, null — невідомо. */
export function resolveListingAccidentHad(listing: Listing): boolean | null {
  const sd = asRecord(listing.source_data);
  const imperiya = asRecord(sd.imperiya);
  if (typeof imperiya.wasAccident === "boolean") return imperiya.wasAccident;
  const condition = asRecord(imperiya.condition);
  if (typeof condition.wasAccident === "boolean") return condition.wasAccident;

  const auto = asRecord(sd.autoData);
  const damageRaw = auto.damageId ?? auto.damage;
  if (typeof damageRaw === "number" || (typeof damageRaw === "string" && damageRaw.trim())) {
    const damageId = Number(damageRaw);
    if (damageId === 1) return false;
    if (damageId === 2) return true;
  }

  const damageName = String(auto.damageName || "").toLowerCase();
  if (damageName) {
    if (/(не був|not in|без дтп|not damaged)/i.test(damageName)) return false;
    if (/(був|після|after|дтп|accident)/i.test(damageName)) return true;
  }

  const flags = asRecord(sd.condition_flags);
  if (typeof flags.accident === "boolean") return flags.accident;
  if (typeof flags.had_accident === "boolean") return flags.had_accident;
  if (typeof flags.dtp === "boolean") return flags.dtp;

  const haystack = [listing.title, listing.description || "", listing.brand, listing.model]
    .filter(Boolean)
    .join(" ");
  if (ACCIDENT_NONE.test(haystack)) return false;
  if (ACCIDENT_HAD.test(haystack)) return true;
  return null;
}

export function formatListingAccident(had: boolean | null): string {
  if (had === true) return "Був у ДТП";
  if (had === false) return "Не був у ДТП";
  return "—";
}
