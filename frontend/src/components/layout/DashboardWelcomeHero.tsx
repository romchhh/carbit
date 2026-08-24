"use client";

import { cn } from "@/lib/utils";

type Props = {
  firstName: string;
  className?: string;
};

export function DashboardWelcomeHero({ firstName, className }: Props) {
  return (
    <section data-tour="welcome-hero" className={cn("mb-4 sm:mb-5", className)}>
      <h1 className="text-[17px] font-bold text-ink sm:text-[18px]">
        Привіт — <span className="text-emerald-dark">{firstName}</span>
      </h1>
    </section>
  );
}
