import Image from "next/image";
import { cn } from "@/lib/utils";

/** Офіційне лого LiqPay (для світлого фону). Джерело: Wikimedia Commons. */
export function LiqPayLogo({
  className = "",
  variant = "color",
  height = 28,
}: {
  className?: string;
  /** color — на світлому фоні; white — лого в світлому «бейджі» для темного футера */
  variant?: "color" | "white";
  height?: number;
}) {
  const width = Math.round(height * (960 / 199));

  const image = (
    <Image
      src="/brand/logo-liqpay.png"
      alt="LiqPay"
      width={width}
      height={height}
      className={cn("h-auto w-auto object-contain", className)}
      style={{ height, width: "auto" }}
      unoptimized
      priority={false}
    />
  );

  if (variant === "white") {
    return (
      <span className="inline-flex items-center rounded-md bg-white px-2.5 py-1.5">
        {image}
      </span>
    );
  }

  return image;
}
