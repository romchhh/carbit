"use client";

import { useLayoutEffect, useRef } from "react";

/** Formatted controlled input that keeps the caret when the value is rewritten (spaces, strip, etc.). */
export function FormattedNumberInput({
  value,
  onChange,
  format,
  placeholder,
  className,
  autoFocus,
  inputMode = "numeric",
  maxLength,
}: {
  value: string;
  onChange: (next: string) => void;
  format?: (raw: string) => string;
  placeholder?: string;
  className?: string;
  autoFocus?: boolean;
  inputMode?: "numeric" | "decimal" | "text";
  maxLength?: number;
}) {
  const ref = useRef<HTMLInputElement>(null);
  const caretRef = useRef<number | null>(null);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el || caretRef.current == null) return;
    const pos = Math.min(caretRef.current, el.value.length);
    el.setSelectionRange(pos, pos);
    caretRef.current = null;
  }, [value]);

  return (
    <input
      ref={ref}
      value={value}
      placeholder={placeholder}
      className={className}
      inputMode={inputMode}
      autoFocus={autoFocus}
      maxLength={maxLength}
      onChange={e => {
        const el = e.target;
        const raw = el.value;
        const start = el.selectionStart ?? raw.length;
        const digitsBefore = countDigits(raw.slice(0, start));
        const next = format ? format(raw) : raw;
        caretRef.current = caretPosForDigitIndex(next, digitsBefore);
        onChange(next);
      }}
    />
  );
}

function countDigits(s: string): number {
  let n = 0;
  for (const ch of s) {
    if (ch >= "0" && ch <= "9") n += 1;
  }
  return n;
}

function caretPosForDigitIndex(formatted: string, digitIndex: number): number {
  if (digitIndex <= 0) return 0;
  let seen = 0;
  for (let i = 0; i < formatted.length; i += 1) {
    const ch = formatted[i];
    if (ch >= "0" && ch <= "9") {
      seen += 1;
      if (seen === digitIndex) return i + 1;
    }
  }
  return formatted.length;
}
