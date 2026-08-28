"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { CarbitLogo } from "@/components/brand/CarbitLogo";

export default function AppSectionError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[app]", error);
  }, [error]);

  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center px-4 py-12 text-center">
      <CarbitLogo variant="full" height={32} className="mx-auto mb-6" />
      <h1 className="text-lg font-bold text-ink">Не вдалось завантажити кабінет</h1>
      <p className="mt-2 max-w-sm text-[13px] leading-relaxed text-muted">
        Спробуйте ще раз. Якщо помилка повторюється — оновіть сторінку або увійдіть заново.
      </p>
      <div className="mt-6 flex w-full max-w-sm flex-col gap-3 sm:max-w-none sm:flex-row sm:justify-center">
        <Button size="xl" className="w-full sm:w-auto" onClick={() => reset()}>
          Спробувати знову
        </Button>
        <Link href="/app/dashboard" className="w-full sm:w-auto">
          <Button variant="secondary" size="xl" className="w-full">
            На головну кабінету
          </Button>
        </Link>
      </div>
    </div>
  );
}
