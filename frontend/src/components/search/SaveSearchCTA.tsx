"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { IconCheck, IconTelegram } from "@/components/icons";
import { UpgradeOffer } from "@/components/billing/UpgradeOffer";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";
import { TelegramConnectPrompt } from "@/components/search/TelegramConnectPrompt";
import { useAuth } from "@/contexts/AuthProvider";
import { cn } from "@/lib/utils";

type Props = {
  onSave: () => void;
  saving?: boolean;
  successMessage?: string | null;
  errorMessage?: string | null;
  limitReached?: boolean;
  telegramConnected?: boolean;
  /** Моніторинг з цими фільтрами уже збережено */
  monitorConnected?: boolean;
  connectedMonitorId?: string | null;
  className?: string;
};

export function SaveSearchCTA({
  onSave,
  saving,
  successMessage,
  errorMessage,
  limitReached,
  telegramConnected,
  monitorConnected,
  connectedMonitorId,
  className,
}: Props) {
  const { user } = useAuth();
  const router = useRouter();
  const [showTgPrompt, setShowTgPrompt] = useState(false);

  const handleConnectClick = () => {
    if (saving || limitReached) return;
    if (monitorConnected && connectedMonitorId) {
      router.push(`/app/monitors/${connectedMonitorId}`);
      return;
    }
    if (!telegramConnected) {
      setShowTgPrompt(true);
      return;
    }
    onSave();
  };

  const connected = Boolean(monitorConnected && connectedMonitorId);

  return (
    <div className={cn("space-y-3", className)}>
      <div
        className={cn(
          "rounded-2xl border px-4 py-3.5 sm:px-5",
          connected
            ? "border-emerald/35 bg-emerald-light/40"
            : "border-[#229ED9]/25 bg-[#E8F4FD]/50",
        )}
        data-tour="save-search"
      >
        <div className="flex flex-col gap-2.5 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <button
            type="button"
            onClick={handleConnectClick}
            disabled={saving || limitReached}
            className={cn(
              "inline-flex w-full items-center justify-center gap-2 rounded-full px-5 py-2.5 text-[13px] font-bold text-white transition-colors sm:w-auto",
              "disabled:cursor-not-allowed disabled:opacity-60",
              connected
                ? "bg-emerald shadow-sm shadow-emerald/25 hover:bg-emerald-dark"
                : "bg-[#229ED9] hover:bg-[#1a8bc4]",
            )}
          >
            {connected ? <IconCheck size={16} strokeWidth={2.5} /> : <IconTelegram size={16} />}
            {saving
              ? "Підключаємо…"
              : connected
                ? "Моніторинг підключено"
                : "Підключити моніторинг"}
          </button>
        </div>

        {successMessage && !connected && (
          <p className="mt-2 text-[12px] font-medium text-emerald-dark">{successMessage}</p>
        )}
        {connected && (
          <p className="mt-2 text-[12px] font-medium text-emerald-dark">
            Ці фільтри вже в «Мої моніторинги». Натисніть, щоб відкрити.
          </p>
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

      <TelegramConnectPrompt
        open={showTgPrompt}
        onClose={() => setShowTgPrompt(false)}
        onContinueWithoutTelegram={onSave}
        onConnected={onSave}
      />
    </div>
  );
}
