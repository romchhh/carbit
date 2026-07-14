"use client";

import Image from "next/image";
import Link from "next/link";
import { IconArrowRight, IconZap } from "@/components/icons";
import { Badge } from "@/components/ui/Badge";
import { AppSection } from "@/components/layout/AppPage";
import { formatSearchDesc } from "@/lib/format-search-desc";
import { cn } from "@/lib/utils";
import type { SearchQuery } from "@/types/api";

type Props = {
  search: SearchQuery;
  /** Якщо false — кнопка «Відкрити» лише для активних (дашборд). */
  alwaysLink?: boolean;
};

export function MonitorSearchCard({ search: s, alwaysLink = true }: Props) {
  const href = `/app/monitors/${s.id}`;
  const showOpen = alwaysLink || s.is_active;

  const body = (
    <AppSection
      className={cn(
        "!bg-white p-4 transition-colors hover:border-emerald/30 sm:p-5",
        !s.is_active && "opacity-60",
      )}
    >
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex min-w-0 flex-1 items-start gap-3">
          <div className="relative h-14 w-[4.5rem] shrink-0 overflow-hidden rounded-xl bg-surface ring-1 ring-border/70 sm:h-16 sm:w-24">
            {s.preview_image ? (
              <Image
                src={s.preview_image}
                alt=""
                fill
                className="object-cover"
                sizes="96px"
                unoptimized
              />
            ) : (
              <div className="flex h-full items-center justify-center text-[10px] font-medium text-muted">
                Немає фото
              </div>
            )}
            <span
              className={cn(
                "absolute left-1.5 top-1.5 h-2 w-2 rounded-full ring-2 ring-white",
                s.is_active ? "bg-emerald" : "bg-border",
              )}
            />
          </div>
          <div className="min-w-0">
            <div className="flex flex-wrap items-center gap-2">
              <span className="truncate text-[15px] font-semibold text-ink">{s.name}</span>
              {s.new_count > 0 && (
                <Badge variant="ink" className="gap-1">
                  <IconZap size={9} /> {alwaysLink ? `${s.new_count} нові` : s.new_count}
                </Badge>
              )}
            </div>
            <p className="mt-1 truncate text-[12px] text-muted">{formatSearchDesc(s.filters)}</p>
          </div>
        </div>

        <div className="flex items-center justify-between gap-4 sm:justify-end">
          <div className="text-left sm:text-right">
            <div
              className={cn(
                "text-[20px] font-black leading-none",
                s.is_active ? "text-emerald-dark" : "text-muted",
              )}
            >
              {s.is_active ? s.total_count : "—"}
            </div>
            <div className="mt-1 text-[10px] uppercase tracking-wide text-muted">авто</div>
          </div>
          {showOpen && (
            alwaysLink ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-emerald/10 px-3 py-2 text-[12px] font-semibold text-emerald-dark">
                Відкрити <IconArrowRight size={11} />
              </span>
            ) : (
              <Link
                href={href}
                className="inline-flex items-center gap-1 rounded-full bg-emerald/10 px-3 py-2 text-[12px] font-semibold text-emerald-dark transition-colors hover:bg-emerald/15"
              >
                Відкрити <IconArrowRight size={11} />
              </Link>
            )
          )}
        </div>
      </div>
    </AppSection>
  );

  if (alwaysLink) {
    return (
      <Link href={href} className="block">
        {body}
      </Link>
    );
  }

  return body;
}
