"use client";

import Image from "next/image";
import {
  listingSourceIcon,
  listingSourceLabel,
} from "@/lib/listing-source";
import { cn } from "@/lib/utils";
import type { Listing, ListingSourceLink } from "@/types/api";

const SOURCE_ORDER = ["auto_ria", "olx", "telegram"] as const;

function rank(source: string): number {
  const i = SOURCE_ORDER.indexOf(source as (typeof SOURCE_ORDER)[number]);
  return i === -1 ? 9 : i;
}

/** Усі джерела оголошення: канонічне + дзеркала (AUTO.RIA першим). */
export function listingSourceLinks(listing: Listing): ListingSourceLink[] {
  const bySource = new Map<string, ListingSourceLink>();
  if (listing.url) {
    bySource.set(listing.source, {
      source: listing.source,
      url: listing.url,
      id: listing.id,
    });
  }
  for (const alt of listing.alternate_sources ?? []) {
    if (!alt?.url || !alt.source) continue;
    if (!bySource.has(alt.source)) {
      bySource.set(alt.source, {
        source: alt.source,
        url: alt.url,
        id: alt.id ?? undefined,
      });
    }
  }
  return [...bySource.values()].sort((a, b) => rank(a.source) - rank(b.source));
}

type Props = {
  listing: Listing;
  className?: string;
  /** Лише іконки без підписів (картки). */
  iconOnly?: boolean;
  size?: "sm" | "md";
  stopPropagation?: boolean;
};

export function SourceLinks({
  listing,
  className,
  iconOnly = false,
  size = "sm",
  stopPropagation = true,
}: Props) {
  const links = listingSourceLinks(listing);
  if (links.length === 0) return null;

  const iconPx = size === "md" ? 18 : 14;
  const pad = size === "md" ? "p-1.5" : "p-1";

  return (
    <div
      className={cn("inline-flex flex-wrap items-center gap-1.5", className)}
      onClick={stopPropagation ? e => e.stopPropagation() : undefined}
      onKeyDown={stopPropagation ? e => e.stopPropagation() : undefined}
    >
      {links.map(link => {
        const icon = listingSourceIcon(link.source);
        const label = listingSourceLabel(link.source);
        return (
          <a
            key={`${link.source}-${link.url}`}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
            title={label}
            aria-label={`Відкрити на ${label}`}
            className={cn(
              "inline-flex items-center gap-1 rounded-md border border-border/80 bg-white/95 shadow-sm transition-colors hover:border-emerald/40 hover:bg-white",
              pad,
              iconOnly ? "" : "pr-2",
            )}
          >
            {icon ? (
              <Image
                src={icon}
                alt=""
                width={iconPx}
                height={iconPx}
                className="rounded-sm object-contain"
                unoptimized
              />
            ) : null}
            {!iconOnly && (
              <span className="text-[10px] font-semibold text-ink">{label}</span>
            )}
          </a>
        );
      })}
    </div>
  );
}
