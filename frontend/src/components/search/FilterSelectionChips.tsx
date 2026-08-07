"use client";

import { BrandIcon } from "@/components/search/BrandIcon";
import { getBrandIconUrl } from "@/lib/search-data/brand-icons";
import { cn } from "@/lib/utils";

type Chip = {
  key: string;
  label: string;
  onRemove: () => void;
  iconBrand?: string;
};

type Props = {
  chips: Chip[];
  className?: string;
};

export function FilterSelectionChips({ chips, className }: Props) {
  if (chips.length === 0) return null;

  return (
    <div className={cn("flex flex-wrap gap-1.5 px-0.5", className)}>
      {chips.map(chip => {
        const iconUrl = chip.iconBrand ? getBrandIconUrl(chip.iconBrand) : null;
        return (
          <button
            key={chip.key}
            type="button"
            onClick={chip.onRemove}
            className="inline-flex max-w-full items-center gap-1.5 rounded-full border border-emerald/25 bg-emerald/8 px-2.5 py-1 text-[12px] font-medium text-emerald-dark transition-colors hover:border-emerald/40 hover:bg-emerald/12"
            title="Прибрати"
          >
            {iconUrl ? <BrandIcon src={iconUrl} size={16} /> : null}
            <span className="truncate">{chip.label}</span>
            <span className="text-emerald-dark/70" aria-hidden>
              ×
            </span>
          </button>
        );
      })}
    </div>
  );
}
