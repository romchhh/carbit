"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";

type PersonalDataConsentCheckboxProps = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
  linkTarget?: "_blank" | "_self";
};

export function PersonalDataConsentCheckbox({
  checked,
  onChange,
  disabled = false,
  className,
  linkTarget = "_blank",
}: PersonalDataConsentCheckboxProps) {
  return (
    <label
      className={cn(
        "flex cursor-pointer items-start gap-2.5 text-[12px] leading-snug text-ink/80",
        disabled && "cursor-not-allowed opacity-60",
        className,
      )}
    >
      <input
        type="checkbox"
        className="mt-0.5 h-4 w-4 shrink-0 rounded border-border accent-emerald-dark"
        checked={checked}
        disabled={disabled}
        onChange={e => onChange(e.target.checked)}
        required
      />
      <span>
        Надаю згоду на обробку моїх персональних даних згідно з{" "}
        <Link
          href="/personal-data"
          target={linkTarget}
          rel={linkTarget === "_blank" ? "noopener noreferrer" : undefined}
          className="font-semibold text-emerald-dark underline underline-offset-2 hover:text-ink"
          onClick={e => e.stopPropagation()}
        >
          порядком
        </Link>{" "}
        їх обробки та на доступ до моєї кредитної історії у будь-якому бюро кредитних історій.
      </span>
    </label>
  );
}
