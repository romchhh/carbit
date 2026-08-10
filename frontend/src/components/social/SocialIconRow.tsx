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
};

export function SocialIconRow({ className, size = "sm" }: Props) {
  const box = size === "sm" ? "h-9 w-9" : "h-10 w-10";
  const icon = size === "sm" ? 16 : 18;

  return (
    <div className={cn("flex items-center justify-center gap-2.5", className)}>
      <a
        href={INSTAGRAM_URL}
        target="_blank"
        rel="noopener noreferrer"
        aria-label={`Instagram @${INSTAGRAM_HANDLE}`}
        className={cn(
          "flex items-center justify-center rounded-full bg-gradient-to-tr from-[#f58529]/15 via-[#dd2a7b]/15 to-[#8134af]/15 text-[#dd2a7b] transition hover:scale-105 hover:brightness-110",
          box,
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
          "flex items-center justify-center rounded-full bg-ink/5 text-ink transition hover:scale-105 hover:bg-ink/10",
          box,
        )}
      >
        <IconTikTok size={icon} />
      </a>
    </div>
  );
}
