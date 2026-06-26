"use client";

import { useRef, KeyboardEvent, ClipboardEvent } from "react";
import { cn } from "@/lib/utils";

interface CodeInputProps {
  length?: number;
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
}

export function CodeInput({ length = 6, value, onChange, disabled }: CodeInputProps) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = value.padEnd(length, " ").slice(0, length).split("");

  const update = (next: string) => {
    const cleaned = next.replace(/\D/g, "").slice(0, length);
    onChange(cleaned);
    if (cleaned.length < length) {
      inputs.current[cleaned.length]?.focus();
    }
  };

  const handleChange = (index: number, char: string) => {
    const digit = char.replace(/\D/g, "").slice(-1);
    const arr = value.split("");
    arr[index] = digit;
    const next = arr.join("").replace(/\s/g, "").slice(0, length);
    onChange(next);
    if (digit && index < length - 1) {
      inputs.current[index + 1]?.focus();
    }
  };

  const handleKeyDown = (index: number, e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Backspace" && !digits[index]?.trim() && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  const handlePaste = (e: ClipboardEvent) => {
    e.preventDefault();
    update(e.clipboardData.getData("text"));
  };

  return (
    <div className="flex gap-2 sm:gap-3 justify-center">
      {Array.from({ length }).map((_, i) => (
        <input
          key={i}
          ref={el => { inputs.current[i] = el; }}
          type="text"
          inputMode="numeric"
          maxLength={1}
          disabled={disabled}
          value={digits[i]?.trim() ?? ""}
          onChange={e => handleChange(i, e.target.value)}
          onKeyDown={e => handleKeyDown(i, e)}
          onPaste={handlePaste}
          onFocus={e => e.target.select()}
          className={cn(
            "w-11 h-14 sm:w-12 sm:h-16 text-center text-[22px] font-black rounded-xl border-2 bg-surface",
            "text-ink focus:outline-none focus:border-emerald focus:ring-2 focus:ring-emerald/20 transition-all",
            digits[i]?.trim() ? "border-emerald/40" : "border-border",
            disabled && "opacity-50 cursor-not-allowed",
          )}
          aria-label={`Цифра ${i + 1}`}
        />
      ))}
    </div>
  );
}
