"use client";

import Image from "next/image";
import Link from "next/link";
import { IconArrowRight, IconEdit, IconTrash, IconZap } from "@/components/icons";
import { Badge } from "@/components/ui/Badge";
import { IosToggle } from "@/components/ui/IosToggle";
import { AppSection } from "@/components/layout/AppPage";
import { formatSearchDesc } from "@/lib/format-search-desc";
import { cn } from "@/lib/utils";
import type { SearchQuery } from "@/types/api";

type Props = {
  search: SearchQuery;
  /** Якщо false — кнопка «Відкрити» лише для активних (дашборд). */
  alwaysLink?: boolean;
  toggling?: boolean;
  deleting?: boolean;
  onActiveChange?: (active: boolean) => void;
  onEdit?: () => void;
  onDelete?: () => void;
};

export function MonitorSearchCard({
  search: s,
  alwaysLink = true,
  toggling = false,
  deleting = false,
  onActiveChange,
  onEdit,
  onDelete,
}: Props) {
  const href = `/app/monitors/${s.id}`;
  const showOpen = alwaysLink || s.is_active;

  return (
    <AppSection
      className={cn(
        "!bg-white p-4 transition-colors hover:border-emerald/30 sm:p-5",
        !s.is_active && "opacity-70",
      )}
    >
      <div className="flex gap-3 sm:gap-4">
        <Link
          href={href}
          className="relative h-16 w-[4.75rem] shrink-0 overflow-hidden rounded-xl bg-surface ring-1 ring-border/70 sm:h-[4.5rem] sm:w-28"
        >
          {s.preview_image ? (
            <Image
              src={s.preview_image}
              alt=""
              fill
              className="object-cover"
              sizes="112px"
              unoptimized
            />
          ) : (
            <div className="flex h-full items-center justify-center text-[10px] font-medium text-muted">
              Немає фото
            </div>
          )}
        </Link>

        <div className="min-w-0 flex-1">
          <div className="flex items-start gap-3">
            <Link href={href} className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-2">
                <span className="truncate text-[15px] font-semibold text-ink">{s.name}</span>
                {s.new_count > 0 && (
                  <Badge variant="ink" className="gap-1">
                    <IconZap size={9} /> {alwaysLink ? `${s.new_count} нові` : s.new_count}
                  </Badge>
                )}
              </div>
              <p className="mt-1 line-clamp-2 text-[12px] leading-relaxed text-muted">
                {formatSearchDesc(s.filters)}
              </p>
            </Link>

            <div className="shrink-0 text-right">
              <div
                className={cn(
                  "text-[22px] font-black leading-none tabular-nums",
                  s.is_active ? "text-emerald-dark" : "text-muted",
                )}
              >
                {s.total_count}
              </div>
              <div className="mt-0.5 text-[10px] uppercase tracking-wide text-muted">авто</div>
            </div>
          </div>

          <div className="mt-3 flex flex-wrap items-center gap-2 border-t border-border/60 pt-3">
            {onActiveChange && (
              <div className="mr-auto flex items-center gap-2">
                <IosToggle
                  checked={s.is_active}
                  disabled={toggling}
                  aria-label={s.is_active ? "Вимкнути моніторинг" : "Увімкнути моніторинг"}
                  onChange={onActiveChange}
                />
                <span className="text-[12px] font-medium text-muted">
                  {s.is_active ? "Активний" : "Пауза"}
                </span>
              </div>
            )}

            <div className="flex items-center gap-1">
              {onEdit && (
                <button
                  type="button"
                  onClick={onEdit}
                  aria-label="Редагувати моніторинг"
                  className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink"
                >
                  <IconEdit size={16} />
                </button>
              )}
              {onDelete && (
                <button
                  type="button"
                  onClick={onDelete}
                  disabled={deleting}
                  aria-label="Видалити моніторинг"
                  className="flex h-9 w-9 items-center justify-center rounded-full text-muted transition-colors hover:bg-red-50 hover:text-red-600 disabled:opacity-50"
                >
                  <IconTrash size={16} />
                </button>
              )}
              {showOpen && (
                <Link
                  href={href}
                  className="ml-1 inline-flex items-center gap-1 rounded-full bg-emerald/10 px-3 py-2 text-[12px] font-semibold text-emerald-dark transition-colors hover:bg-emerald/15"
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
