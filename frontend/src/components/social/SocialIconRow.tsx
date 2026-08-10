import { IconInstagram, IconTikTok } from "@/components/icons";
import {
  INSTAGRAM_HANDLE,
  INSTAGRAM_URL,
  TIKTOK_HANDLE,
  TIKTOK_URL,
} from "@/lib/social-links";
import { cn } from "@/lib/utils";

type Props = {
  className?: string;
  size?: "sm" | "md";
  /** light — на темному фоні (футер) */
  variant?: "default" | "light";
};

export function SocialIconRow({ className, size = "sm", variant = "default" }: Props) {
  const box = size === "sm" ? "h-9 w-9" : "h-10 w-10";
  const icon = size === "sm" ? 16 : 18;
  const light = variant === "light";

  return (
    <div className={cn("flex items-center justify-center gap-2.5", className)}>
      <a
        href={INSTAGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Instagram @${INSTAGRAM_HANDLE}`}
        className={cn(
          "flex items-center justify-center rounded-full transition hover:scale-105",
          box,
          light
            ? "bg-white/10 text-[#f58529] hover:bg-white/15"
            : "bg-gradient-to-tr from-[#f58529]/15 via-[#dd2a7b]/15 to-[#8134af]/15 text-[#dd2a7b] hover:brightness-110",
        )}
      >
        <IconInstagram size={icon} />
      </a>
      <a
        href={TIKTOK_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`TikTok @${TIKTOK_HANDLE}`}
        className={cn(
          "flex items-center justify-center rounded-full transition hover:scale-105",
          box,
          light
            ? "bg-white/10 text-white hover:bg-white/15"
            : "bg-ink/5 text-ink hover:bg-ink/10",
        )}
      >
        <IconTikTok size={icon} />
      </a>
    </div>
  );
}
