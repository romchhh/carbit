import { ButtonHTMLAttributes, forwardRef } from "react";
import { cn } from "@/lib/utils";
import { IconArrowRight } from "@/components/icons";

type Variant = "primary" | "secondary" | "ghost" | "emerald" | "danger";
type Size = "sm" | "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  showArrow?: boolean;
}

const variants: Record<Variant, string> = {
  primary:   "bg-ink text-white hover:bg-ink-2 font-semibold shadow-md shadow-ink/15 hover:shadow-lg hover:shadow-ink/25",
  emerald:   "bg-emerald text-white hover:bg-emerald-dark font-semibold shadow-md shadow-emerald/25 hover:shadow-lg hover:shadow-emerald/35",
  secondary: "bg-white border border-border text-ink hover:bg-surface font-medium shadow-sm",
  ghost:     "text-muted hover:text-ink hover:bg-surface font-medium",
  danger:    "text-red-500 hover:bg-red-50 border border-border font-medium",
};
const sizes: Record<Size, string> = {
  sm: "px-2 py-1 text-[11px] rounded-full",
  md: "px-2.5 py-1.5 text-[12px] rounded-full",
  lg: "px-3.5 py-2 text-[13px] rounded-full",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = "primary", size = "md", loading, showArrow, className, children, disabled, ...props }, ref) => (
    <button ref={ref} disabled={disabled || loading}
      className={cn(
        "group inline-flex items-center justify-center gap-2.5 transition-all duration-300 hover:-translate-y-0.5 active:translate-y-0 active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:translate-y-0",
        variants[variant], sizes[size], className
      )} {...props}>
      {loading && (
        <svg className="animate-spin w-3.5 h-3.5" viewBox="0 0 24 24" fill="none">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 0 1 8-8V0C5.4 0 0 5.4 0 12h4Z"/>
        </svg>
      )}
      {children}
      {showArrow && !loading && (
        <span className={cn(
          "flex items-center justify-center rounded-full transition-all duration-300 group-hover:translate-x-0.5",
          size === "sm" ? "w-4 h-4" : size === "lg" ? "w-5 h-5" : "w-5 h-5",
          variant === "primary" || variant === "emerald"
            ? "bg-white/15 group-hover:bg-white/25"
            : "bg-ink/5 group-hover:bg-emerald/10 group-hover:text-emerald-dark"
        )}>
          <IconArrowRight size={size === "sm" ? 10 : size === "lg" ? 12 : 11} />
        </span>
      )}
    </button>
  )
);
Button.displayName = "Button";
