import { cn } from "@/lib/utils";

type AlertVariant = "info" | "success" | "warning" | "danger";

const VARIANT: Record<
  AlertVariant,
  { box: string; title: string; body: string; icon: string }
> = {
  info: {
    box: "border-sky-200 bg-sky-50",
    title: "text-sky-950",
    body: "text-sky-900/75",
    icon: "bg-sky-500",
  },
  success: {
    box: "border-emerald/30 bg-emerald-light/50",
    title: "text-emerald-dark",
    body: "text-emerald-dark/80",
    icon: "bg-emerald",
  },
  warning: {
    box: "border-amber-200 bg-amber-50",
    title: "text-amber-950",
    body: "text-amber-900/75",
    icon: "bg-amber-500",
  },
  danger: {
    box: "border-red-200 bg-red-50",
    title: "text-red-800",
    body: "text-red-700/80",
    icon: "bg-red-500",
  },
};

type Props = {
  variant?: AlertVariant;
  title: string;
  children?: React.ReactNode;
  action?: React.ReactNode;
  className?: string;
  role?: "status" | "alert";
};

export function Alert({
  variant = "info",
  title,
  children,
  action,
  className,
  role = "status",
}: Props) {
  const styles = VARIANT[variant];

  return (
    <div
      role={role}
      className={cn(
        "flex flex-col gap-3 rounded-2xl border px-3.5 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-4 sm:py-3.5",
        styles.box,
        className,
      )}
    >
      <div className="flex min-w-0 gap-2.5">
        <span
          className={cn("mt-1.5 h-2 w-2 shrink-0 rounded-full", styles.icon)}
          aria-hidden
        />
        <div className="min-w-0">
          <p className={cn("text-[13px] font-bold leading-snug", styles.title)}>{title}</p>
          {children && (
            <div className={cn("mt-0.5 text-[12px] leading-relaxed", styles.body)}>{children}</div>
          )}
        </div>
      </div>
      {action && <div className="shrink-0 sm:pl-2">{action}</div>}
    </div>
  );
}
