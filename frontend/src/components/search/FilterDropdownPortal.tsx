"use client";

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import type { CSSProperties, ReactNode, RefObject } from "react";
import { useAnchoredDropdownStyle } from "@/components/search/useAnchoredDropdownStyle";
import { cn } from "@/lib/utils";

type Props = {
  open: boolean;
  anchorRef: RefObject<HTMLElement | null>;
  children: ReactNode;
  className?: string;
  id?: string;
};

export function FilterDropdownPortal({ open, anchorRef, children, className, id }: Props) {
  const [mounted, setMounted] = useState(false);
  const style = useAnchoredDropdownStyle(open, anchorRef);

  useEffect(() => {
    setMounted(true);
  }, []);

  if (!mounted || !open || !style) return null;

  return createPortal(
    <div
      id={id}
      style={style as CSSProperties}
      className={cn(
        "overflow-hidden rounded-xl border border-border bg-white shadow-[0_16px_40px_-12px_rgba(10,12,14,0.28)] ring-1 ring-black/5",
        className,
      )}
    >
      {children}
    </div>,
    document.body,
  );
}
