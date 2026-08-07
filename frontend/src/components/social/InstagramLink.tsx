"use client";

import { cn } from "@/lib/utils";
import { INSTAGRAM_HANDLE, INSTAGRAM_URL } from "@/lib/social-links";
import { IconInstagram } from "@/components/icons";

type Props = {
  className?: string;
  showHandle?: boolean;
  variant?: "default" | "light" | "pill";
  size?: "sm" | "md";
};

export function InstagramLink({
  className,
  showHandle = true,
  variant = "default",
  size = "md",
}: Props) {
  const iconSize = size === "sm" ? 16 : 18;

  return (
    <a
      href={INSTAGRAM_URL}
      target="_blank"
      rel="noopener noreferrer"
      className={cn(
        "inline-flex items-center gap-2 transition-colors",
        variant === "default" && "text-muted hover:text-ink",
        variant === "light" && "text-white/70 hover:text-white",
        variant === "pill" &&
          "rounded-full bg-gradient-to-r from-[#f58529] via-[#dd2a7b] to-[#8134af] px-3.5 py-2 text-[12px] font-semibold text-white shadow-md shadow-[#dd2a7b]/20 hover:brightness-110",
        className,
      )}
      aria-label={`Instagram @${INSTAGRAM_HANDLE}`}
    >
      <IconInstagram size={iconSize} className={variant === "pill" ? "text-white" : undefined} />
      {showHandle && <span>@{INSTAGRAM_HANDLE}</span>}
    </a>
  );
}
