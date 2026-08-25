"use client";

import type { ReactNode } from "react";
import { FormattedNumberInput } from "@/components/search/FormattedNumberInput";
import { FilterSubsectionLabel } from "@/components/search/FilterSubsectionLabel";
import { cn } from "@/lib/utils";

type Props = {
  label: string;
  from: string;
  to: string;
  onChange: (from: string, to: string) => void;
  format?: (value: string) => string;
  placeholderFrom?: string;
  placeholderTo?: string;
  suffix?: string;
  inputMode?: "numeric" | "decimal";
  className?: string;
  trailing?: ReactNode;
};

export function FilterInlineRange({
  label,
  from,
  to,
  onChange,
  format,
  placeholderFrom = "Від",
  placeholderTo = "До",
  suffix,
  inputMode = "numeric",
  className,
  trailing,
}: Props) {
  return (
    <div className={cn("space-y-2.5", className)}>
      <FilterSubsectionLabel trailing={trailing}>
        {label}
        {suffix ? <span className="font-normal text-muted"> · {suffix}</span> : null}
      </FilterSubsectionLabel>
      <div className="grid grid-cols-[1fr_auto_1fr] items-center gap-2">
        <FormattedNumberInput
          value={from}
          onChange={v => onChange(v, to)}
          format={format}
          placeholder={placeholderFrom}
          inputMode={inputMode}
          className="input-field !py-2 text-center"
        />
        <span className="text-[12px] text-muted">—</span>
        <FormattedNumberInput
          value={to}
          onChange={v => onChange(from, v)}
          format={format}
          placeholder={placeholderTo}
          inputMode={inputMode}
          className="input-field !py-2 text-center"
        />
      </div>
    </div>
  );
}
