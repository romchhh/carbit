"use client";

import { useCallback, useEffect, useState } from "react";
import { VinCheckModal } from "@/components/listings/VinCheckModal";
import { VinCheckResultView } from "@/components/listings/VinCheckResultView";
import { getApiErrorMessage, vinCheck } from "@/lib/api";
import { cn } from "@/lib/utils";
import { hasVinCheck, normalizeVin } from "@/lib/vin-check";
import type { Listing, VinCheckResult } from "@/types/api";

type Props = {
  listing: Listing;
  className?: string;
  size?: "sm" | "md";
  /** Показувати збережений результат на сторінці (не лише в модалці). */
  showSavedOnPage?: boolean;
  onResult?: (result: VinCheckResult) => void;
};

export function VinCheckButton({
  listing,
  className,
  size = "sm",
  showSavedOnPage = false,
  onResult,
}: Props) {
  const vin = normalizeVin(listing.vin);
  const [modalOpen, setModalOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<VinCheckResult | null>(listing.vin_check ?? null);

  useEffect(() => {
    if (listing.vin_check) setResult(listing.vin_check);
  }, [listing.vin_check]);

  const runCheck = useCallback(async () => {
    if (!vin) return;
    setModalOpen(true);
    if (result || loading) return;
    setLoading(true);
    setError(null);
    try {
      const data = await vinCheck.get(vin, listing.id);
      setResult(data);
      onResult?.(data);
    } catch (err) {
      setError(getApiErrorMessage(err, "Не вдалося перевірити VIN"));
    } finally {
      setLoading(false);
    }
  }, [listing.id, loading, onResult, result, vin]);

  if (!hasVinCheck(listing) || !vin) return null;

  const saved = result ?? listing.vin_check ?? null;

  return (
    <div className={cn("w-full", className)} onClick={e => e.stopPropagation()}>
      {showSavedOnPage && saved && (
        <div className="mb-3 rounded-2xl border border-emerald/20 bg-emerald/5 p-3.5 sm:p-4">
          <p className="mb-2 text-[11px] font-semibold uppercase tracking-wide text-emerald-dark">
            Збережена перевірка VIN
          </p>
          <VinCheckResultView result={saved} />
        </div>
      )}

      <button
        type="button"
        onClick={() => void runCheck()}
        disabled={loading}
        className={cn(
          "inline-flex w-full items-center justify-center rounded-full border border-emerald/30 bg-emerald/10 font-semibold text-emerald-dark transition-colors hover:border-emerald/50 hover:bg-emerald/15 disabled:opacity-60 sm:w-auto",
          size === "sm" ? "px-3 py-1.5 text-[11px]" : "px-4 py-2 text-[13px]",
        )}
      >
        {loading
          ? "Перевіряємо…"
          : saved
            ? "Відкрити перевірку VIN"
            : "Перевірити за VIN"}
      </button>

      <VinCheckModal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        result={result}
        loading={loading}
        error={error}
      />
    </div>
  );
}
