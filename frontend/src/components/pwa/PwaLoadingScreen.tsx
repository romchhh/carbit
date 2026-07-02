import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { cn } from "@/lib/utils";

type Props = {
  size?: number;
  className?: string;
  fixed?: boolean;
};

export function PwaLoadingScreen({ size = 96, className, fixed = true }: Props) {
  const logoHeight = Math.max(Math.round(size * 0.38), 28);

  return (
    <div
      className={cn(
        "flex min-h-[100dvh] items-center justify-center bg-[#EEF0F4]",
        fixed && "fixed inset-0 z-[9999]",
        className,
      )}
      role="status"
      aria-label="Завантаження Carbit"
    >
      <div
        className="rounded-[28px] bg-white shadow-[0_12px_40px_-8px_rgba(10,12,14,0.22)] ring-1 ring-black/[0.06]"
        style={{ padding: Math.round(size * 0.28) }}
      >
        <CarbitLogo variant="full" height={logoHeight} priority />
      </div>
    </div>
  );
}
