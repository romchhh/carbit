"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconX } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { CodeInput } from "@/components/auth/CodeInput";
import { PhoneInput, normalizePhoneForApi } from "@/components/auth/PhoneInput";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError } from "@/lib/api";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";

type Tab = "login" | "register";
type PhoneStep = "form" | "verify";
type CodeChannel = "sms" | "telegram";

type Props = {
  open: boolean;
  onClose: () => void;
  onAuthenticated: () => void;
};

export function AuthGateModal({ open, onClose, onAuthenticated }: Props) {
  const { sendPhoneCode, verifyPhoneCode } = useAuth();

  const [tab, setTab] = useState<Tab>("login");
  const [phoneStep, setPhoneStep] = useState<PhoneStep>("form");
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [phone, setPhone] = useState("");
  const [phoneCode, setPhoneCode] = useState("");
  const [phoneName, setPhoneName] = useState("");
  const [codeChannel, setCodeChannel] = useState<CodeChannel>("sms");

  useEffect(() => {
    if (!open) return;
    lockBodyScroll();
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      unlockBodyScroll();
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  const resetMessages = () => {
    setError("");
    setSuccess("");
  };

  const handleTabChange = (next: Tab) => {
    setTab(next);
    setPhoneStep("form");
    setPhoneCode("");
    setCodeChannel("sms");
    resetMessages();
  };

  const startResendCooldown = () => {
    setResendCooldown(60);
    const interval = setInterval(() => {
      setResendCooldown(prev => {
        if (prev <= 1) {
          clearInterval(interval);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  const requestCode = async (delivery: "auto" | "sms" = "auto") => {
    const normalized = normalizePhoneForApi(phone);
    if (normalized.length < 12) {
      setError("Введіть повний номер телефону");
      return;
    }
    if (tab === "register" && !phoneName.trim()) {
      setError("Вкажіть ім'я");
      return;
    }

    resetMessages();
    setLoading(true);
    try {
      const result = await sendPhoneCode(
        normalized,
        tab === "login" ? "login" : "register",
        tab === "register" ? phoneName.trim() : undefined,
        delivery,
      );
      setPhoneStep("verify");
      setCodeChannel(result.channel === "telegram" ? "telegram" : "sms");
      setSuccess(result.message);
      startResendCooldown();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося надіслати код");
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneSendCode = async (e: React.FormEvent) => {
    e.preventDefault();
    await requestCode("auto");
  };

  const handlePhoneVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (phoneCode.length !== 6) {
      setError("Введіть 6-значний код");
      return;
    }
    const normalized = normalizePhoneForApi(phone);
    setLoading(true);
    try {
      await verifyPhoneCode(
        normalized,
        phoneCode,
        tab === "login" ? "login" : "register",
        tab === "register" ? phoneName.trim() : undefined,
        true,
      );
      onAuthenticated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Помилка підтвердження");
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneResend = async (delivery: "auto" | "sms" = "auto") => {
    if (resendCooldown > 0) return;
    await requestCode(delivery);
  };

  const channelHint =
    codeChannel === "telegram"
      ? "Код надіслано в Telegram."
      : `Код надіслано SMS на +380 ${phone}`;

  return (
    <div
      className="fixed inset-0 z-[130] flex items-end justify-center p-0 sm:items-center sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-gate-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-ink/60 backdrop-blur-sm"
        aria-label="Закрити"
        onClick={onClose}
      />

      <div className="relative z-10 flex max-h-[92dvh] w-full max-w-[440px] flex-col overflow-hidden rounded-t-[1.5rem] border border-border/60 bg-white shadow-2xl sm:max-h-[90vh] sm:rounded-[1.5rem]">
        <div className="flex items-center justify-between border-b border-border/60 px-5 py-4">
          <CarbitLogo variant="full" height={28} />
          <button
            type="button"
            onClick={onClose}
            className="flex h-9 w-9 items-center justify-center rounded-full border border-border text-muted transition-colors hover:border-ink/20 hover:text-ink"
            aria-label="Закрити"
          >
            <IconX size={18} />
          </button>
        </div>

        <div className="overflow-y-auto px-5 py-5 sm:px-6 sm:py-6">
          {phoneStep === "verify" ? (
            <>
              <h2 id="auth-gate-title" className="text-[22px] font-black tracking-[-0.03em] text-ink">
                Підтвердіть номер
              </h2>
              <p className="mt-2 text-[13px] leading-relaxed text-muted">{channelHint}</p>

              <form onSubmit={handlePhoneVerify} className="mt-5 space-y-4">
                <CodeInput value={phoneCode} onChange={setPhoneCode} disabled={loading} />

                {success && (
                  <p className="rounded-lg border border-emerald/20 bg-emerald-light/50 px-3 py-2 text-center text-[13px] text-emerald-dark">
                    {success}
                  </p>
                )}
                {error && (
                  <p className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-center text-[13px] text-red-600">
                    {error}
                  </p>
                )}

                <Button
                  type="submit"
                  loading={loading}
                  size="md"
                  variant="emerald"
                  showArrow
                  className="w-full"
                  disabled={phoneCode.length !== 6}
                >
                  {tab === "login" ? "Увійти" : "Створити акаунт"}
                </Button>

                <div className="space-y-2 text-center text-[12px] text-muted">
                  <p>
                    Не отримали код?{" "}
                    <button
                      type="button"
                      onClick={() => void handlePhoneResend("auto")}
                      disabled={resendCooldown > 0 || loading}
                      className={cn(
                        "font-semibold",
                        resendCooldown > 0 ? "cursor-not-allowed text-muted" : "text-emerald-dark hover:underline",
                      )}
                    >
                      {resendCooldown > 0 ? `Повторити через ${resendCooldown}с` : "Надіслати знову"}
                    </button>
                  </p>
                  {tab === "login" && codeChannel === "telegram" && (
                    <p>
                      Telegram недоступний?{" "}
                      <button
                        type="button"
                        onClick={() => void handlePhoneResend("sms")}
                        disabled={resendCooldown > 0 || loading}
                        className={cn(
                          "font-semibold",
                          resendCooldown > 0 ? "cursor-not-allowed text-muted" : "text-emerald-dark hover:underline",
                        )}
                      >
                        Надіслати SMS
                      </button>
                    </p>
                  )}
                </div>
              </form>
            </>
          ) : (
            <>
              <h2 id="auth-gate-title" className="text-[20px] font-black tracking-[-0.03em] text-ink">
                {tab === "login" ? "Вхід" : "Реєстрація"}
              </h2>

              <div className="mt-4 flex rounded-full border border-border/60 bg-surface p-1">
                {(["login", "register"] as Tab[]).map(t => (
                  <button
                    key={t}
                    type="button"
                    onClick={() => handleTabChange(t)}
                    className={cn(
                      "flex-1 rounded-full py-2 text-[13px] font-semibold transition-all",
                      tab === t ? "bg-ink text-white shadow-md" : "text-muted hover:text-ink",
                    )}
                  >
                    {t === "login" ? "Вхід" : "Реєстрація"}
                  </button>
                ))}
              </div>

              <p className="mt-4 text-[13px] leading-relaxed text-muted">
                {tab === "login"
                  ? "Код надішлемо в Telegram, якщо він привʼязаний, інакше — SMS."
                  : "Код підтвердження надішлемо SMS."}
              </p>

              <form onSubmit={handlePhoneSendCode} className="mt-4 space-y-3">
                {tab === "register" && (
                  <input
                    type="text"
                    placeholder="Ім'я"
                    className="auth-input"
                    value={phoneName}
                    onChange={e => setPhoneName(e.target.value)}
                    required
                    autoComplete="name"
                  />
                )}
                <PhoneInput value={phone} onChange={setPhone} disabled={loading} />

                {success && (
                  <p className="rounded-lg border border-emerald/20 bg-emerald-light/50 px-3 py-2 text-[13px] text-emerald-dark">
                    {success}
                  </p>
                )}
                {error && (
                  <p className="rounded-lg border border-red-100 bg-red-50 px-3 py-2 text-[13px] text-red-600">
                    {error}
                  </p>
                )}

                <Button type="submit" loading={loading} size="md" variant="emerald" showArrow className="w-full">
                  {tab === "login" ? "Отримати код" : "Надіслати код SMS"}
                </Button>
              </form>

              <p className="mt-4 text-center text-[11px] text-muted">
                <Link href="/terms" className="hover:text-ink" onClick={onClose}>
                  Умови
                </Link>
                {" · "}
                <Link href="/privacy" className="hover:text-ink" onClick={onClose}>
                  Конфіденційність
                </Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
