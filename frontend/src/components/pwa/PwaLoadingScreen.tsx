import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { cn } from "@/lib/utils";

type Props = {
  size?: number;
  className?: string;
  fixed?: boolean;
  "aria-hidden"?: boolean;
};

export function PwaLoadingScreen({
  size = 128,
  className,
  fixed = true,
  "aria-hidden": ariaHidden,
}: Props) {
  return (
    <div
      className={cn(
        "flex min-h-[100dvh] items-center justify-center bg-[#EEF0F4]",
        fixed && "fixed inset-0 z-[9999]",
        className,
      )}
      role="status"
      aria-label="Завантаження Carbit"
      aria-hidden={ariaHidden}
    >
      <CarbitLogo variant="icon" height={size} priority className="drop-shadow-sm" />
    </div>
  );
}
