"use client";

import Image from "next/image";
import { useRouter } from "next/navigation";
import { ListingPriceDisplay } from "@/components/listings/ListingPriceDisplay";
import { LANDING_SAMPLE_PRESETS, type LandingSamplePreset } from "@/lib/landing-sample-searches";
import { saveSearchDraft } from "@/lib/search-draft";
import { cn, formatMileage } from "@/lib/utils";

type Props = {
  className?: string;
  onSelectPreset?: (preset: LandingSamplePreset) => void;
};

function SampleCard({
  preset,
  onSelect,
}: {
  preset: LandingSamplePreset;
  onSelect: (preset: LandingSamplePreset) => void;
}) {
  const listing = preset.listing;
  const image = listing.images[0];

  return (
    <button
      type="button"
      onClick={() => onSelect(preset)}
      className="group flex w-full items-stretch gap-2.5 overflow-hidden rounded-xl border border-border/80 bg-white p-2 text-left shadow-sm transition-shadow hover:border-emerald/30 hover:shadow-md sm:gap-3 sm:p-2.5"
    >
      <div className="relative h-[72px] w-[96px] shrink-0 overflow-hidden rounded-lg bg-surface sm:h-[76px] sm:w-[104px]">
        {image ? (
          <Image
            src={image}
            alt={listing.title}
            fill
            className="object-cover transition-transform duration-300 group-hover:scale-[1.03]"
            sizes="104px"
          />
        ) : null}
      </div>
      <div className="flex min-w-0 flex-1 flex-col justify-center gap-0.5 py-0.5">
        <p className="truncate text-[11px] font-semibold text-emerald-dark">{preset.title}</p>
        <p className="truncate text-[13px] font-bold leading-tight text-ink">
          {listing.year} · {formatMileage(listing.mileage)}
        </p>
        <p className="truncate text-[11px] text-muted">{listing.region}</p>
        <ListingPriceDisplay
          listing={listing}
          displayCurrency="USD"
          priceClassName="text-[14px] font-bold text-ink"
          showBadge={false}
        />
      </div>
    </button>
  );
}

export function HomeSearchSampleResults({ className, onSelectPreset }: Props) {
  const router = useRouter();

  const handleSelect = (preset: LandingSamplePreset) => {
    onSelectPreset?.(preset);
    saveSearchDraft(preset.filters, { freshness: "all" });
    router.push("/search");
  };

  return (
    <div className={cn("min-w-0", className)}>
      <div className="mb-3 lg:mb-4">
        <h3 className="text-[15px] font-bold tracking-[-0.02em] text-ink sm:text-[16px]">
          Приклади з ринку
        </h3>
        <p className="mt-0.5 text-[12px] leading-snug text-muted">
          Натисніть, щоб побачити актуальні оголошення
        </p>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-1">
        {LANDING_SAMPLE_PRESETS.map(preset => (
          <SampleCard key={preset.id} preset={preset} onSelect={handleSelect} />
        ))}
      </div>
    </div>
  );
}
