"use client";

import { useEffect } from "react";
import Link from "next/link";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { LiqPayLogo } from "@/components/brand/LiqPayLogo";
import { IconCheck } from "@/components/icons";
import { CtaLink } from "@/components/ui/CtaLink";
import { useAuth } from "@/contexts/AuthProvider";
import { PLAN_LABELS } from "@/lib/utils";

export default function PaymentSuccessPage() {
  const { user, refreshUser } = useAuth();

  useEffect(() => {
    void refreshUser();
  }, [refreshUser]);

  const planLabel = user?.plan ? (PLAN_LABELS[user.plan] ?? user.plan) : null;

  return (
    <div className="relative flex min-h-[min(70vh,640px)] flex-col items-center justify-center overflow-hidden px-4 py-10 sm:py-14">
      <div
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(ellipse_at_50%_0%,rgba(0,200,150,0.18),transparent_55%)]"
        aria-hidden
      />
      <div
        className="pointer-events-none absolute -right-16 top-8 h-48 w-48 rounded-full bg-emerald/10 blur-3xl motion-safe:animate-float"
        aria-hidden
      />

      <div className="relative w-full max-w-md text-center">
        <Link href="/app/dashboard" className="mb-8 inline-flex justify-center">
          <CarbitLogo variant="full" height={32} />
        </Link>

        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-emerald text-white shadow-lg shadow-emerald/30 motion-safe:animate-fade-up">
          <IconCheck size={28} />
        </div>

        <h1 className="mt-6 text-[26px] font-black tracking-tight text-ink motion-safe:animate-fade-up sm:text-[30px]">
          Оплату прийнято
        </h1>
        <p className="mt-3 text-[14px] leading-relaxed text-muted motion-safe:animate-fade-up-delay sm:text-[15px]">
          Дякуємо! Підписка активується протягом кількох секунд.
          {planLabel ? (
            <>
              {" "}
              Зараз у вас тариф <span className="font-semibold text-ink">{planLabel}</span>.
            </>
          ) : null}
        </p>

        <div className="mt-8 flex flex-col items-center gap-3 motion-safe:animate-fade-up-delay">
          <CtaLink href="/app/dashboard" variant="emerald" size="lg" className="w-full max-w-xs justify-center">
            До кабінету
          </CtaLink>
          <Link
            href="/app/billing"
            className="text-[13px] font-medium text-muted transition-colors hover:text-ink"
          >
            Керувати підпискою
          </Link>
        </div>

        <div className="mt-10 flex justify-center opacity-80">
          <LiqPayLogo height={22} />
        </div>
      </div>
    </div>
  );
}
