"use client";

import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { IconGlobe } from "@/components/icons";
import { buildAutoRiaDetailSections } from "@/lib/auto-ria-details";
import type { Listing } from "@/types/api";

type Props = {
  listing: Listing;
  /** Якщо опис уже показаний окремо на сторінці. */
  omitDescription?: boolean;
};

export function AutoRiaListingDetails({ listing, omitDescription = false }: Props) {
  if (!listing.source_data || listing.source !== "auto_ria") return null;

  const sourceData = {
    ...listing.source_data,
    ...(listing.description && !listing.source_data.description && !omitDescription
      ? { description: listing.description }
      : {}),
  };

  const sections = buildAutoRiaDetailSections(sourceData, listing.url).filter(
    section => !(omitDescription && section.title === "Опис"),
  );
  if (!sections.length) return null;

  return (
    <div className="space-y-4">
      <h3 className="text-[13px] font-bold text-ink">Дані AUTO.RIA</h3>
      <div className="space-y-4">
        {sections.map(section => (
          <div key={section.title} className="rounded-2xl border border-border/70 bg-surface/40 p-4">
            <h4 className="text-[11px] font-bold uppercase tracking-wide text-muted">{section.title}</h4>
            <dl className="mt-3 grid grid-cols-1 gap-2.5 sm:grid-cols-2">
              {section.rows.map(row => (
                <div
                  key={`${section.title}-${row.label}-${row.value}`}
                  className={row.kind === "link" ? "sm:col-span-2" : "min-w-0"}
                >
                  <dt className="text-[10px] font-semibold uppercase tracking-wide text-muted">{row.label}</dt>
                  <dd className="mt-1">
                    {row.kind === "link" && row.href ? (
                      <Link href={row.href} target="_blank" rel="noopener noreferrer">
                        <Button variant="secondary" size="sm" className="gap-1.5">
                          <IconGlobe size={14} />
                          {row.value}
                        </Button>
                      </Link>
                    ) : row.kind === "color" ? (
                      <span className="inline-flex items-center gap-2 text-[13px] font-medium text-ink">
                        {row.colorHex && (
                          <span
                            className="h-5 w-5 shrink-0 rounded-full border border-border/80 shadow-sm"
                            style={{ backgroundColor: row.colorHex }}
                            aria-hidden
                          />
                        )}
                        {row.value}
                      </span>
                    ) : (
                      <span className="break-words text-[13px] font-medium leading-snug text-ink whitespace-pre-wrap">
                        {row.value}
                      </span>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        ))}
      </div>
    </div>
  );
}
