"use client";

import { useEffect, useState } from "react";
import { pickWelcomeMotivation, WELCOME_MOTIVATIONS } from "@/lib/welcome-motivations";
import { cn } from "@/lib/utils";

type Props = {
  firstName: string;
  className?: string;
};

export function DashboardWelcomeHero({ firstName, className }: Props) {
  const [motivation, setMotivation] = useState(WELCOME_MOTIVATIONS[0] ?? "");

  useEffect(() => {
    setMotivation(pickWelcomeMotivation());
  }, []);

  return (
    <section
      data-tour="welcome-hero"
      className={cn("relative mb-5 sm:mb-7", className)}
    >
      <h1 className="text-[22px] font-black leading-tight tracking-tight text-ink sm:text-[30px]">
        Привіт, <span className="text-emerald-dark">{firstName}</span>
      </h1>
      <p className="mt-1.5 max-w-[36rem] text-[14px] leading-relaxed text-muted sm:mt-2 sm:text-[15px]">
        {motivation}
      </p>
    </section>
  );
}
