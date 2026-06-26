import Link from "next/link";
import { cn } from "@/lib/utils";
import { IconArrowRight } from "@/components/icons";

type Variant = "primary" | "emerald" | "ghost" | "white";

const variants: Record<Variant, { btn: string; arrow: string }> = {
  primary: {
    btn: "bg-ink text-white hover:bg-ink-2 shadow-lg shadow-ink/20 hover:shadow-xl hover:shadow-ink/30",
    arrow: "bg-white/15 group-hover:bg-emerald group-hover:text-white",
  },
  emerald: {
    btn: "bg-emerald text-white hover:bg-emerald-dark shadow-lg shadow-emerald/30 hover:shadow-xl hover:shadow-emerald/40",
    arrow: "bg-white/20 group-hover:bg-white group-hover:text-emerald-dark",
  },
  white: {
    btn: "bg-white text-ink hover:bg-white/90 shadow-lg shadow-black/10",
    arrow: "bg-ink/5 group-hover:bg-emerald group-hover:text-white",
  },
  ghost: {
    btn: "bg-white/10 text-white border border-white/25 hover:bg-white/20 backdrop-blur-sm",
    arrow: "bg-white/15 group-hover:bg-white group-hover:text-ink",
  },
};

interface CtaLinkProps {
  href: string;
  children: React.ReactNode;
  variant?: Variant;
  size?: "md" | "lg";
  className?: string;
}

export function CtaLink({ href, children, variant = "primary", size = "md", className }: CtaLinkProps) {
  const v = variants[variant];
  return (
    <Link
      href={href}
      className={cn(
        "group inline-flex items-center gap-3 font-semibold rounded-full transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98]",
        size === "lg" ? "text-[13px] px-4 py-2" : "text-[12px] px-3.5 py-1.5",
        v.btn,
        className
      )}
    >
      <span>{children}</span>
      <span
        className={cn(
          "flex items-center justify-center rounded-full transition-all duration-300 group-hover:translate-x-0.5",
          size === "lg" ? "w-5 h-5" : "w-5 h-5",
          v.arrow
        )}
      >
        <IconArrowRight size={size === "lg" ? 12 : 11} strokeWidth={2.2} />
      </span>
    </Link>
  );
}
