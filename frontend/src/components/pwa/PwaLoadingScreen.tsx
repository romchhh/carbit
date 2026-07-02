import { PwaAppIcon } from "@/components/pwa/PwaAppIcon";
import { cn } from "@/lib/utils";

type Props = {
  size?: number;
  className?: string;
  fixed?: boolean;
};

export function PwaLoadingScreen({ size = 96, className, fixed = true }: Props) {
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
      <div className="rounded-[28px] shadow-[0_12px_40px_-8px_rgba(10,12,14,0.22)] ring-1 ring-black/5">
        <PwaAppIcon size={size} />
      </div>
    </div>
  );
}
