import { cn, publishedAgoLabel, timeAgo } from "@/lib/utils";

type Props = {
  date: string | null | undefined;
  className?: string;
  /** Короткий варіант для бейджа на фото: «5 хв тому» */
  short?: boolean;
};

export function PublishedTimeBadge({ date, className, short = false }: Props) {
  const label = short ? timeAgo(date) : publishedAgoLabel(date);
  if (!label) return null;

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full bg-ink/75 px-2 py-0.5 text-[10px] font-medium text-white backdrop-blur-sm",
        className,
      )}
    >
      {!short && <span aria-hidden>🕐</span>}
      {short ? `🕐 ${label}` : label}
    </span>
  );
}
