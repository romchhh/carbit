"use client";

import Link from "next/link";
import { IconTelegram } from "@/components/icons";
import { UpgradeOffer } from "@/components/billing/UpgradeOffer";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";
import { useAuth } from "@/contexts/AuthProvider";
import { cn } from "@/lib/utils";

type Props = {
  onSave: () => void;
  saving?: boolean;
  successMessage?: string | null;
  errorMessage?: string | null;
  limitReached?: boolean;
  telegramConnected?: boolean;
  className?: string;
};

export function SaveSearchCTA({
  onSave,
  saving,
  successMessage,
  errorMessage,
  limitReached,
  telegramConnected,
  className,
}: Props) {
  const { user } = useAuth();

  return (
    <div className={cn("space-y-3", className)}>
      <div
        className="rounded-2xl border border-[#229ED9]/25 bg-[#E8F4FD]/50 px-4 py-3.5 sm:px-5"
        data-tour="save-search"
      >
        <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <button
            type="button"
            onClick={onSave}
            disabled={saving || limitReached}
            className={cn(
              "inline-flex w-full items-center justify-center gap-2 rounded-full bg-[#229ED9] px-5 py-2.5 text-[13px] font-bold text-white transition-colors hover:bg-[#1a8bc4] sm:w-auto",
              "disabled:cursor-not-allowed disabled:opacity-60",
            )}
          >
            <IconTelegram size={16} />
            {saving ? "Підключаємо…" : "Підключити моніторинг"}
          </button>

          {!telegramConnected && (
            <p className="text-center text-[12px] text-muted sm:text-right">
              Спочатку{" "}
              <Link
                href="/app/account"
                className="font-semibold text-[#229ED9] underline-offset-2 hover:underline"
              >
                підключіть Telegram
              </Link>
            </p>
          )}
        </div>

        {successMessage && (
          <p className="mt-2 text-[12px] font-medium text-emerald-dark">{successMessage}</p>
        )}
        {errorMessage && !limitReached && (
          <p className="mt-2 text-[12px] font-medium text-red-600">{errorMessage}</p>
        )}
      </div>

      {limitReached && <UpgradeOffer title="Ліміт моніторингів вичерпано" compact />}

      {!limitReached && user && (user.plan === "free" || Boolean(successMessage)) && (
        <SubscriptionPitch
          variant="compact"
          planId={user.plan}
          searchesLimit={user.searches_limit}
          isTrial={Boolean(user.is_trial_active)}
        />
      )}
    </div>
  );
}
