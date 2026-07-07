import Image from "next/image";
import { Badge } from "@/components/ui/Badge";
import { listingSourceIcon, listingSourceLabel } from "@/lib/listing-source";
import { cn } from "@/lib/utils";

type Props = {
  source: string;
  className?: string;
  variant?: "gray" | "outline";
  showLabel?: boolean;
};

export function SourceBadge({
  source,
  className,
  variant = "gray",
  showLabel = true,
}: Props) {
  const icon = listingSourceIcon(source);
  const label = listingSourceLabel(source);

  return (
    <Badge
      variant={variant}
      className={cn("inline-flex items-center gap-1.5 bg-white/95 text-[10px] shadow-sm", className)}
    >
      {icon ? (
        <Image src={icon} alt="" width={14} height={14} className="rounded-sm object-contain" unoptimized />
      ) : null}
      {showLabel ? label : null}
    </Badge>
  );
}
