import { cn } from "@/lib/utils";

type V = "emerald" | "gray" | "ink" | "red" | "outline";
const v: Record<V, string> = {
  emerald: "bg-emerald-light text-emerald-dark",
  gray:    "bg-surface text-muted",
  ink:     "bg-ink text-white",
  red:     "bg-red-50 text-red-600",
  outline: "border border-border text-muted bg-white",
};
export function Badge({ children, variant = "gray", className }: { children: React.ReactNode; variant?: V; className?: string }) {
  return <span className={cn("inline-flex items-center px-3 py-1 rounded-full text-[12px] font-semibold tracking-wide", v[variant], className)}>{children}</span>;
}
