"use client";

import Link from "next/link";
import { IconArrowRight, IconEdit, IconTrash, IconZap } from "@/components/icons";
import { Badge } from "@/components/ui/Badge";
import { IosToggle } from "@/components/ui/IosToggle";
import { AppSection } from "@/components/layout/AppPage";
import { ListingPhoto } from "@/components/listings/ListingPhoto";
import { formatSearchDesc } from "@/lib/format-search-desc";
import { cn } from "@/lib/utils";
import type { SearchQuery } from "@/types/api";

type Props = {
  search: SearchQuery;
  /** Якщо false — кнопка «Відкрити» лише для активних (дашборд). */
  alwaysLink?: boolean;
  /** Компактна картка для горизонтального скролу на дашборді. */
  variant?: "default" | "compact";
  toggling?: boolean;
  deleting?: boolean;
  onActiveChange?: (active: boolean) => void;
  onEdit?: () => void;
  onDelete?: () => void;
  className?: string;
};

export function MonitorSearchCard({
  search: s,
  alwaysLink = true,
  variant = "default",
  toggling = false,
  deleting = false,
  onActiveChange,
  onEdit,
  onDelete,
  className,
}: Props) {
  const href = `/app/monitors/${s.id}`;
  const showOpen = alwaysLink || s.is_active;
  const compact = variant === "compact";

  if (compact) {
    return (
      <article
        className={cn(
          "flex w-[288px] shrink-0 flex-col overflow-hidden rounded-xl border border-border/70 bg-white transition-all hover:border-emerald/35 hover:shadow-md hover:shadow-emerald/5",
          !s.is_active && "opacity-80",
          className,
        )}
      >
        <Link href={href} className="relative block h-[120px] w-full bg-surface">
          <ListingPhoto
            src={s.preview_image}
            alt=""
            sizes="288px"
            logoClassName="h-7"
          />
          {s.new_count > 0 ? (
            <span className="absolute left-2 top-2 rounded-full bg-ink px-2 py-0.5 text-[10px] font-bold text-white">
              {s.new_count} нові
            </span>
          ) : null}
          {(s.price_drop_count ?? 0) > 0 ? (
            <span className="absolute right-2 top-2 rounded-full border border-rose-200 bg-rose-50 px-2 py-0.5 text-[10px] font-bold text-rose-700">
              −{s.price_drop_count}
            </span>
          ) : null}
        </Link>

        <div className="flex min-h-0 flex-1 flex-col p-3">
          <Link href={href} className="min-w-0">
            <div className="line-clamp-1 text-[14px] font-semibold text-ink">{s.name}</div>
            <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-muted">
              {formatSearchDesc(s.filters)}
            </p>
          </Link>

          <div className="mt-3 flex items-center justify-between gap-2 border-t border-border/60 pt-3">
            <div className="flex items-center gap-2">
              {onActiveChange ? (
                <>
                  <IosToggle
                    checked={s.is_active}
                    disabled={toggling}
                    aria-label={s.is_active ? "Вимкнути моніторинг" : "Увімкнути моніторинг"}
                    onChange={onActiveChange}
                  />
                  <span className="text-[11px] font-medium text-muted">
                    {s.is_active ? "Активний" : "Пауза"}
                  </span>
                </>
              ) : null}
            </div>
            <div className="text-right">
              <div
                className={cn(
                  "text-[20px] font-black leading-none tabular-nums",
                  s.is_active ? "text-emerald-dark" : "text-muted",
                )}
              >
                {s.total_count}
              </div>
              <div className="text-[9px] uppercase tracking-wide text-muted">авто</div>
            </div>
          </div>

          {showOpen ? (
            <Link
              href={href}
              className="mt-3 inline-flex items-center justify-center gap-1 rounded-lg bg-emerald/10 py-2 text-[12px] font-semibold text-emerald-dark transition-colors hover:bg-emerald/15"
            >
              Відкрити <IconArrowRight size={11} />
            </Link>
          ) : null}
        </div>
      </article>
    );
  }

  return (
    <AppSection
      className={cn(
        "!bg-white p-3 transition-colors hover:border-emerald/30 sm:p-5 lg:p-6",
        !s.is_active && "opacity-70",
        className,
      )}
    >
      <div className="flex gap-2.5 sm:gap-4 lg:gap-5">
        <Link
          href={href}
          className="relative h-14 w-[4.25rem] shrink-0 overflow-hidden rounded-xl bg-surface ring-1 ring-border/70 sm:h-[4.5rem] sm:w-28 lg:h-28 lg:w-40 lg:rounded-2xl"
        >
          <ListingPhoto
            src={s.preview_image}
            alt=""
            sizes="(min-width: 1024px) 160px, 112px"
            logoClassName="h-4 lg:h-7"
          />
        </Link>

        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-2 sm:gap-3 lg:gap-4">
            <Link href={href} className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-1.5 sm:gap-2">
                <span className="truncate text-[14px] font-semibold text-ink sm:text-[15px] lg:text-[18px]">
                  {s.name}
                </span>
                {s.new_count > 0 && (
                  <Badge variant="ink" className="gap-1 lg:text-[12px] lg:px-2.5 lg:py-1">
                    <IconZap size={9} /> {alwaysLink ? `${s.new_count} нові` : s.new_count}
                  </Badge>
                )}
                {(s.price_drop_count ?? 0) > 0 && (
                  <Badge
                    variant="outline"
                    className="gap-1 border-rose-200 bg-rose-50 text-rose-700 lg:text-[12px] lg:px-2.5 lg:py-1"
                  >
                    −{s.price_drop_count} цін
                  </Badge>
                )}
              </div>
              <p className="mt-0.5 line-clamp-2 text-[11px] leading-relaxed text-muted sm:mt-1 sm:text-[12px] lg:mt-1.5 lg:line-clamp-3 lg:text-[14px]">
                {formatSearchDesc(s.filters)}
              </p>
            </Link>

            <div className="shrink-0 text-right">
              <div
                className={cn(
                  "text-[18px] font-black leading-none tabular-nums sm:text-[22px] lg:text-[28px]",
                  s.is_active ? "text-emerald-dark" : "text-muted",
                )}
              >
                {s.total_count}
              </div>
              <div className="mt-0.5 text-[9px] uppercase tracking-wide text-muted sm:text-[10px] lg:mt-1 lg:text-[11px]">
                авто
              </div>
            </div>
          </div>

          <div className="mt-2.5 flex flex-nowrap items-center gap-1 border-t border-border/60 pt-2.5 sm:mt-3 sm:gap-2 sm:pt-3 lg:mt-4 lg:pt-4">
            {onActiveChange && (
              <div className="mr-auto flex min-w-0 items-center gap-1.5 sm:gap-2">
                <IosToggle
                  checked={s.is_active}
                  disabled={toggling}
                  aria-label={s.is_active ? "Вимкнути моніторинг" : "Увімкнути моніторинг"}
                  onChange={onActiveChange}
                />
                <span className="truncate text-[11px] font-medium text-muted sm:text-[12px] lg:text-[13px]">
                  {s.is_active ? "Активний" : "Пауза"}
                </span>
              </div>
            )}

            <div className="flex shrink-0 items-center gap-0.5 sm:gap-1 lg:gap-1.5">
              {onEdit && (
                <button
                  type="button"
                  onClick={onEdit}
                  aria-label="Редагувати моніторинг"
                  className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink sm:h-9 sm:w-9 lg:h-10 lg:w-10"
                >
                  <IconEdit size={15} />
                </button>
              )}
              {onDelete && (
                <button
                  type="button"
                  onClick={onDelete}
                  disabled={deleting}
                  aria-label="Видалити моніторинг"
                  className="flex h-8 w-8 items-center justify-center rounded-full text-muted transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50 sm:h-9 sm:w-9 lg:h-10 lg:w-10"
                >
                  <IconTrash size={15} />
                </button>
              )}
              {showOpen && (
                <Link
                  href={href}
                  className="ml-0.5 inline-flex items-center gap-0.5 rounded-full bg-emerald/10 px-2.5 py-1.5 text-[11px] font-semibold text-emerald-dark transition-colors hover:bg-emerald/15 sm:ml-1 sm:gap-1 sm:px-3 sm:py-2 sm:text-[12px] lg:px-4 lg:py-2.5 lg:text-[13px]"
                >
                  Відкрити <IconArrowRight size={11} />
                </Link>
              )}
            </div>
          </div>
        </div>
      </div>
    </AppSection>
  );
}
