"use client";

import { useEffect, useState, type CSSProperties, type RefObject } from "react";

const DROPDOWN_Z_INDEX = 200;

export function useAnchoredDropdownStyle(
  open: boolean,
  anchorRef: RefObject<HTMLElement | null>,
  gap = 6,
): CSSProperties | null {
  const [style, setStyle] = useState<CSSProperties | null>(null);

  useEffect(() => {
    if (!open) {
      setStyle(null);
      return;
    }

    const update = () => {
      const anchor = anchorRef.current;
      if (!anchor) return;
      const rect = anchor.getBoundingClientRect();
      const viewportPadding = 8;
      const maxWidth = Math.min(rect.width, window.innerWidth - viewportPadding * 2);
      const left = Math.min(
        Math.max(viewportPadding, rect.left),
        window.innerWidth - maxWidth - viewportPadding,
      );
      const panelMaxHeight = Math.min(288, window.innerHeight - rect.bottom - gap - viewportPadding);

      setStyle({
        position: "fixed",
        top: rect.bottom + gap,
        left,
        width: maxWidth,
        maxHeight: panelMaxHeight > 120 ? panelMaxHeight : undefined,
        zIndex: DROPDOWN_Z_INDEX,
      });
    };

    update();
    window.addEventListener("resize", update);
    window.addEventListener("scroll", update, true);
    return () => {
      window.removeEventListener("resize", update);
      window.removeEventListener("scroll", update, true);
    };
  }, [open, anchorRef, gap]);

  return open ? style : null;
}
