"use client";

import Link from "next/link";
import { CarbitLogo } from "@/components/brand/CarbitLogo";

export function PublicListingShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#eef0f4]">
      <header className="sticky top-0 z-40 border-b border-border/60 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-[980px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link href="/" className="shrink-0">
            <CarbitLogo variant="full" height={28} />
          </Link>
          <div className="flex items-center gap-2">
            <Link
              href="/auth/login"
              className="rounded-full border border-border px-3.5 py-2 text-[13px] font-semibold text-ink transition-colors hover:border-ink/20 hover:bg-surface"
            >
              Увійти
            </Link>
            <Link
              href="/auth/login?tab=register"
              className="rounded-full bg-emerald px-3.5 py-2 text-[13px] font-semibold text-white transition-colors hover:bg-emerald-dark"
            >
              Спробувати
            </Link>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-[980px] px-4 py-5 sm:px-6 sm:py-8">{children}</main>
    </div>
  );
}
