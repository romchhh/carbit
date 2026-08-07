"use client";

import { useEffect } from "react";
import Image from "next/image";
import { IconInstagram, IconX } from "@/components/icons";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";
import {
  dismissInstagramFollowPrompt,
  markInstagramFollowPromptFollowed,
} from "@/lib/instagram-follow-prompt";
import {
  INSTAGRAM_HANDLE,
  INSTAGRAM_PREVIEW_IMAGE,
  INSTAGRAM_URL,
} from "@/lib/social-links";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function InstagramFollowModal({ open, onClose }: Props) {
  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    return () => unlockBodyScroll();
  }, [open]);

  if (!open) return null;

  const close = () => {
    dismissInstagramFollowPrompt();
    onClose();
  };

  const follow = () => {
    markInstagramFollowPromptFollowed();
    window.open(INSTAGRAM_URL, "_blank", "noopener,noreferrer");
    onClose();
  };

  return (
    <div
      className="fixed inset-0 z-[120] flex items-end justify-center p-4 sm:items-center sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="instagram-follow-title"
    >
      <button
        type="button"
        aria-label="Закрити"
        className="absolute inset-0 bg-ink/55 backdrop-blur-[6px]"
        onClick={close}
      />

      <div
        className={cn(
          "relative w-full max-w-[420px] overflow-hidden rounded-[28px] bg-white shadow-[0_24px_80px_-12px_rgba(0,0,0,0.35)]",
        )}
      >
        <button
          type="button"
          onClick={close}
          className="absolute right-3 top-3 z-10 flex h-9 w-9 items-center justify-center rounded-full bg-black/35 text-white backdrop-blur-sm transition-colors hover:bg-black/50"
          aria-label="Закрити"
        >
          <IconX size={16} />
        </button>

        <div className="relative aspect-[4/3] w-full bg-[#fafafa]">
          <Image
            src={INSTAGRAM_PREVIEW_IMAGE}
            alt="Профіль Carbit в Instagram"
            fill
            className="object-cover object-top"
            sizes="420px"
            priority
          />
          <div className="absolute inset-x-0 bottom-0 h-20 bg-gradient-to-t from-black/35 to-transparent" />
          <div className="absolute bottom-3 left-4 flex items-center gap-2 text-white drop-shadow-sm">
            <span className="flex h-8 w-8 items-center justify-center rounded-full bg-gradient-to-tr from-[#f58529] via-[#dd2a7b] to-[#8134af]">
              <IconInstagram size={16} className="text-white" />
            </span>
            <span className="text-[14px] font-bold tracking-tight">@{INSTAGRAM_HANDLE}</span>
          </div>
        </div>

        <div className="px-5 pb-5 pt-4 sm:px-6 sm:pb-6">
          <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-[#dd2a7b]">
            Instagram
          </p>
          <h2
            id="instagram-follow-title"
            className="mt-1.5 text-[20px] font-bold leading-snug tracking-tight text-ink sm:text-[22px]"
          >
            Підпишись на Carbit — будь у курсі новин і свіжих авто
          </h2>
          <p className="mt-2 text-[13px] leading-relaxed text-muted">
            Фото з ринку, оновлення сервісу та корисні підказки для перекупників — у стрічці
            Instagram.
          </p>

          <div className="mt-5 flex flex-col gap-2.5 sm:flex-row">
            <button
              type="button"
              onClick={follow}
              className="inline-flex flex-1 items-center justify-center gap-2 rounded-full bg-gradient-to-r from-[#f58529] via-[#dd2a7b] to-[#8134af] px-5 py-3.5 text-[14px] font-bold text-white shadow-lg shadow-[#dd2a7b]/25 transition-all hover:brightness-110"
            >
              <IconInstagram size={18} />
              Підписатися
            </button>
            <button
              type="button"
              onClick={close}
              className="inline-flex flex-1 items-center justify-center rounded-full border border-border bg-surface px-5 py-3.5 text-[14px] font-semibold text-ink transition-colors hover:bg-white"
            >
              Пізніше
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
