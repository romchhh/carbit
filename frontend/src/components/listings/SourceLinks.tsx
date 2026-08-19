"use client";

import Image from "next/image";
import {
  listingOpenLabel,
  listingSourceIcon,
  listingSourceLabel,
} from "@/lib/listing-source";
import { Button } from "@/components/ui/Button";
import { IconGlobe } from "@/components/icons";
import { cn } from "@/lib/utils";
import type { Listing, ListingSourceLink } from "@/types/api";

const SOURCE_ORDER = ["auto_ria", "olx", "car_market", "imperiya", "udrive", "telegram"] as const;

function rank(source: string): number {
  const i = SOURCE_ORDER.indexOf(source as (typeof SOURCE_ORDER)[number]);
  return i === -1 ? 9 : i;
}

/** Усі джерела оголошення: канонічне + дзеркала (AUTO.RIA першим). */
export function listingSourceLinks(
  listing: Listing,
  opts?: { alternatesOnly?: boolean },
): ListingSourceLink[] {
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
  const links = [...bySource.values()].sort((a, b) => rank(a.source) - rank(b.source));
  if (opts?.alternatesOnly) {
    return links.filter(link => link.source !== listing.source);
  }
  return links;
}

/** Скільки майданчиків стоїть за карткою (канонічне + дзеркала). */
export function listingOfferCount(listing: Listing): number {
  return Math.max(1, listingSourceLinks(listing).length);
}

/** Об'єднує дзеркала з кількох копій оголошення, без дублікатів джерела. */
export function mergeSourceLinks(
  ...groups: Array<ListingSourceLink[] | null | undefined>
): ListingSourceLink[] {
  const bySource = new Map<string, ListingSourceLink>();
  for (const group of groups) {
    for (const link of group ?? []) {
      if (!link?.source || !link?.url) continue;
      if (!bySource.has(link.source)) {
        bySource.set(link.source, {
          source: link.source,
          url: link.url,
          id: link.id ?? undefined,
        });
      }
    }
  }
  return [...bySource.values()].sort((a, b) => rank(a.source) - rank(b.source));
}

/** Підвантаження з БД не повинно затирати дзеркала, знайдені в живому пошуку. */
export function keepListingMirrors(
  fresh: Listing,
  ...prior: Array<Listing | null | undefined>
): Listing {
  return {
    ...fresh,
    alternate_sources: mergeSourceLinks(
      fresh.alternate_sources,
      ...prior.map(item => item?.alternate_sources),
    ),
  };
}

type Props = {
  listing: Listing;
  className?: string;
  /** Лише іконки без підписів (картки). */
  iconOnly?: boolean;
  /** Лише дзеркала, без канонічного джерела («Також на …»). */
  alternatesOnly?: boolean;
  size?: "sm" | "md";
  stopPropagation?: boolean;
};

export function SourceLinks({
  listing,
  className,
  iconOnly = false,
  alternatesOnly = false,
  size = "sm",
  stopPropagation = true,
}: Props) {
  const links = listingSourceLinks(listing, { alternatesOnly });
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

/** Кнопки «Відкрити на …» для кожного майданчика (без дубля «Також на» зверху). */
export function ListingOpenCta({
  listing,
  className,
}: {
  listing: Listing;
  className?: string;
}) {
  const links = listingSourceLinks(listing);
  if (links.length === 0) return null;
  return (
    <div className={cn("flex flex-col gap-2", className)}>
      {links.map((link, index) => {
        const icon = listingSourceIcon(link.source);
        return (
          <a
            key={`${link.source}-${link.url}`}
            href={link.url}
            target="_blank"
            rel="noopener noreferrer"
          >
            <Button
              variant={index === 0 ? "emerald" : "secondary"}
              size="lg"
              className={cn(
                "w-full gap-2 py-3 text-[15px] font-bold",
                index > 0 && "border-border text-ink",
              )}
            >
              {icon ? (
                <Image src={icon} alt="" width={18} height={18} className="rounded-sm object-contain" unoptimized />
              ) : (
                <IconGlobe size={18} />
              )}
              {listingOpenLabel(link.source)}
            </Button>
          </a>
        );
      })}
    </div>
  );
}
