"use client";

import { cn } from "@/lib/utils";

type Props = {
  value: string;
  onChange: (value: string) => void;
  disabled?: boolean;
  className?: string;
  placeholder?: string;
};

function formatPhoneInput(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  let normalized = digits;
  if (normalized.startsWith("380")) {
    normalized = normalized.slice(3, 12);
  } else if (normalized.startsWith("80")) {
    normalized = normalized.slice(2, 11);
  } else if (normalized.startsWith("0")) {
    normalized = normalized.slice(1, 10);
  }
  normalized = normalized.slice(0, 9);

  const parts = [
    normalized.slice(0, 2),
    normalized.slice(2, 5),
    normalized.slice(5, 7),
    normalized.slice(7, 9),
  ].filter(Boolean);

  if (!parts.length) return "";
  if (parts.length === 1) return parts[0];
  if (parts.length === 2) return `${parts[0]} ${parts[1]}`;
  if (parts.length === 3) return `${parts[0]} ${parts[1]} ${parts[2]}`;
  return `${parts[0]} ${parts[1]} ${parts[2]} ${parts[3]}`;
}

export function normalizePhoneForApi(value: string): string {
  const digits = value.replace(/\D/g, "");
  if (digits.startsWith("380")) return digits.slice(0, 12);
  if (digits.startsWith("80") && digits.length >= 11) return `3${digits}`.slice(0, 12);
  if (digits.startsWith("0")) return `38${digits}`.slice(0, 12);
  return `380${digits}`.slice(0, 12);
}

export function PhoneInput({
  value,
  onChange,
  disabled,
  className,
  placeholder = "67 123 45 67",
}: Props) {
  return (
    <div className={cn("auth-input-wrap", className)}>
      <span className="shrink-0 text-[14px] font-semibold text-muted">+380</span>
      <input
        type="tel"
        inputMode="numeric"
        autoComplete="tel-national"
        placeholder={placeholder}
        className="auth-input-inner"
        value={value}
        disabled={disabled}
        onChange={event => onChange(formatPhoneInput(event.target.value))}
      />
    </div>
  );
}
