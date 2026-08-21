import { cn } from "@/lib/utils";

type AppPageProps = {
  title?: string;
  description?: string;
  action?: React.ReactNode;
  wide?: boolean;
  /** Компактна колонка для форм (акаунт тощо) — не розтягується на всю ширину island. */
  narrow?: boolean;
  tourId?: string;
  children: React.ReactNode;
  className?: string;
};

export function AppPage({
  title,
  description,
  action,
  wide,
  narrow,
  tourId,
  children,
  className,
}: AppPageProps) {
  return (
    <div
      data-tour={tourId}
      className={cn(
        "mx-auto w-full lg:mx-0",
        narrow
          ? "max-w-[760px] lg:max-w-[880px]"
          : wide
            ? "max-w-[920px] lg:max-w-none"
            : "max-w-[760px] lg:max-w-[1100px]",
        className,
      )}
    >
      {(title || action) && (
        <header className="mb-6 flex flex-col gap-4 sm:mb-7 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0">
            {title && (
              <h1 className="text-[22px] font-black tracking-tight text-ink sm:text-[26px]">{title}</h1>
            )}
            {description && (
              <p className="mt-1.5 max-w-3xl text-[13px] leading-relaxed text-muted">{description}</p>
            )}
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </header>
      )}
      {children}
    </div>
  );
}

type AppSectionProps = React.ComponentPropsWithoutRef<"section"> & {
  children: React.ReactNode;
  className?: string;
};

export function AppSection({ children, className, ...props }: AppSectionProps) {
  return (
    <section
      className={cn("rounded-2xl border border-border/50 bg-surface/30 p-4 sm:p-6", className)}
      {...props}
    >
      {children}
    </section>
  );
}

/** Група секцій на сторінці акаунта / довгих формах. */
export function AppSectionGroup({
  id,
  label,
  children,
  className,
}: {
  id?: string;
  label: string;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div id={id} className={cn("scroll-mt-28 space-y-3", className)}>
      <h2 className="px-0.5 text-[11px] font-bold uppercase tracking-[0.12em] text-muted">{label}</h2>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

export function AppSectionHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-4 flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0">
        {eyebrow && (
          <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted">{eyebrow}</div>
        )}
        <div className={cn("font-black text-ink", eyebrow ? "mt-1 text-[18px] sm:text-[20px]" : "text-[16px]")}>
          {title}
        </div>
        {description && <p className="mt-1 text-[13px] leading-relaxed text-muted">{description}</p>}
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}

type AppEmptyProps = {
  children: React.ReactNode;
  className?: string;
};

export function AppEmpty({ children, className }: AppEmptyProps) {
  return (
    <div className={cn("rounded-2xl border border-dashed border-border/70 bg-surface/40 px-6 py-12 text-center", className)}>
      {children}
    </div>
  );
}

export function AppLoading() {
  return (
    <div className="flex justify-center py-20">
      <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
    </div>
  );
}

export function AppStatGrid({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={cn("grid grid-cols-2 gap-3 sm:gap-4 lg:grid-cols-4", className)}>
      {children}
    </div>
  );
}

export function AppStatCard({
  label,
  value,
  sub,
  accent,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="rounded-2xl border border-border/40 bg-white px-4 py-4 sm:px-5 sm:py-5">
      <div className="text-[11px] font-medium uppercase tracking-wide text-muted">{label}</div>
      <div className="mt-2 text-[26px] font-black leading-none tracking-tight text-ink sm:text-[28px]">{value}</div>
      {sub && (
        <div className={cn("mt-2 text-[11px] leading-snug", accent ? "font-semibold text-emerald-dark" : "text-muted")}>
          {sub}
        </div>
      )}
    </div>
  );
}
