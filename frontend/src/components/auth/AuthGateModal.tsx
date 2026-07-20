"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconEye, IconLock, IconMail, IconX } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { CodeInput } from "@/components/auth/CodeInput";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError, auth as authApi } from "@/lib/api";
import { getRememberMePreference, getSavedEmail } from "@/lib/auth-storage";
import { lockBodyScroll, unlockBodyScroll } from "@/lib/scroll-lock";

type Tab = "login" | "register";
type RegisterStep = "form" | "verify";

type Props = {
  open: boolean;
  onClose: () => void;
  onAuthenticated: () => void;
};

function GoogleLogo({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" fill="#4285F4" />
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" fill="#34A853" />
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62Z" fill="#FBBC05" />
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" fill="#EA4335" />
    </svg>
  );
}

function TelegramLogo({ size = 18 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z" />
    </svg>
  );
}

export function AuthGateModal({ open, onClose, onAuthenticated }: Props) {
  const { login, sendRegisterCode, verifyRegisterCode, resendRegisterCode } = useAuth();

  const [tab, setTab] = useState<Tab>("login");
  const [registerStep, setRegisterStep] = useState<RegisterStep>("form");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [code, setCode] = useState("");
  const [rememberMe, setRememberMe] = useState(true);

  useEffect(() => {
    if (!open) return;
    setRememberMe(getRememberMePreference());
    const savedEmail = getSavedEmail();
    if (savedEmail) setEmail(savedEmail);
  }, [open]);

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
    setRegisterStep("form");
    setCode("");
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();

    if (tab === "register" && password.length < 8) {
      setError("Пароль має містити щонайменше 8 символів");
      return;
    }

    setLoading(true);
    try {
      if (tab === "login") {
        await login(email.trim(), password, rememberMe);
        onAuthenticated();
      } else {
        await sendRegisterCode(email.trim(), name.trim(), password);
        setRegisterStep("verify");
        setSuccess("Код надіслано на вашу пошту");
        startResendCooldown();
      }
    } catch (err) {
      if (err instanceof ApiError) {
        const messages: Record<string, string> = {
          "Invalid credentials": "Невірний email або пароль",
          "Email already registered": "Цей email вже зареєстрований",
        };
        setError(messages[err.message] ?? err.message);
      } else {
        setError("Не вдалося підключитися до сервера. Спробуйте пізніше.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (code.length !== 6) {
      setError("Введіть 6-значний код");
      return;
    }
    setLoading(true);
    try {
      await verifyRegisterCode(email.trim(), code);
      onAuthenticated();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Помилка підтвердження");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    resetMessages();
    setLoading(true);
    try {
      await resendRegisterCode(email.trim());
      setSuccess("Новий код надіслано");
      startResendCooldown();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося надіслати код");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = authApi.googleLoginUrl();
  };

  const handleTelegramLogin = async () => {
    resetMessages();
    setLoading(true);
    try {
      const { bot_url } = await authApi.telegramLoginUrl();
      window.open(bot_url, "_blank", "noopener,noreferrer");
      setSuccess("Відкрийте Telegram і натисніть «Увійти в кабінет»");
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 503
          ? "Telegram-бот не налаштовано"
          : err instanceof ApiError
            ? err.message
            : "Не вдалося відкрити Telegram",
      );
    } finally {
      setLoading(false);
    }
  };

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
          {registerStep === "verify" ? (
            <>
              <h2 id="auth-gate-title" className="text-[22px] font-black tracking-[-0.03em] text-ink">
                Підтвердіть email
              </h2>
              <p className="mt-2 text-[13px] leading-relaxed text-muted">
                Код надіслано на <strong className="text-ink">{email}</strong>
              </p>

              <form onSubmit={handleVerify} className="mt-5 space-y-4">
                <CodeInput value={code} onChange={setCode} disabled={loading} />

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

                <Button type="submit" loading={loading} size="md" variant="emerald" showArrow className="w-full" disabled={code.length !== 6}>
                  Переглянути результати
                </Button>

                <p className="text-center text-[12px] text-muted">
                  Не отримали код?{" "}
                  <button
                    type="button"
                    onClick={handleResend}
                    disabled={resendCooldown > 0 || loading}
                    className={cn(
                      "font-semibold",
                      resendCooldown > 0 ? "cursor-not-allowed text-muted" : "text-emerald-dark hover:underline",
                    )}
                  >
                    {resendCooldown > 0 ? `Повторити через ${resendCooldown}с` : "Надіслати знову"}
                  </button>
                </p>
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

              {tab === "login" ? (
                <div className="mt-4 flex gap-2">
                  <button
                    type="button"
                    disabled={loading}
                    onClick={handleGoogleLogin}
                    className="flex min-h-[52px] flex-1 flex-col items-center justify-center gap-1 rounded-xl border border-[#747775] bg-white px-2 py-2 text-[#1f1f1f] transition-all hover:border-[#1f1f1f]/30 hover:shadow-sm disabled:opacity-50"
                  >
                    <GoogleLogo />
                    <span className="text-[10px] font-medium">Google</span>
                  </button>
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => void handleTelegramLogin()}
                    className="flex min-h-[52px] flex-1 flex-col items-center justify-center gap-1 rounded-xl bg-[#2481cc] px-2 py-2 text-white transition-colors hover:bg-[#1d6fad] disabled:opacity-50"
                  >
                    <TelegramLogo />
                    <span className="text-[10px] font-medium">Telegram</span>
                  </button>
                </div>
              ) : (
                <button
                  type="button"
                  disabled={loading}
                  onClick={handleGoogleLogin}
                  className="mt-4 flex min-h-[52px] w-full items-center justify-center gap-3 rounded-xl border border-[#747775] bg-white px-3 py-3 text-[#1f1f1f] transition-all hover:border-[#1f1f1f]/30 hover:shadow-sm disabled:opacity-50"
                >
                  <GoogleLogo size={20} />
                  <span className="text-[14px] font-semibold">Google</span>
                </button>
              )}

              <div className="my-4 flex items-center gap-3">
                <div className="h-px flex-1 bg-border" />
                <span className="text-[11px] text-muted">email</span>
                <div className="h-px flex-1 bg-border" />
              </div>

              <form onSubmit={handleSubmit} className="space-y-3">
                {tab === "register" && (
                  <input
                    type="text"
                    placeholder="Ім'я"
                    className="auth-input"
                    value={name}
                    onChange={e => setName(e.target.value)}
                    required
                    autoComplete="name"
                  />
                )}

                <div className="auth-input-wrap">
                  <IconMail size={16} className="shrink-0 text-muted" />
                  <input
                    type="email"
                    placeholder="Email"
                    className="auth-input-inner"
                    value={email}
                    onChange={e => setEmail(e.target.value)}
                    required
                    autoComplete="email"
                  />
                </div>

                <div className="auth-input-wrap">
                  <IconLock size={16} className="shrink-0 text-muted" />
                  <input
                    type={showPass ? "text" : "password"}
                    placeholder="Пароль"
                    className="auth-input-inner"
                    value={password}
                    onChange={e => setPassword(e.target.value)}
                    required
                    minLength={tab === "register" ? 8 : 1}
                    autoComplete={tab === "login" ? "current-password" : "new-password"}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPass(v => !v)}
                    className="p-1 text-muted transition-colors hover:text-ink"
                    aria-label={showPass ? "Сховати пароль" : "Показати пароль"}
                  >
                    <IconEye size={16} />
                  </button>
                </div>

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
                  {tab === "login" ? "Увійти" : "Продовжити"}
                </Button>
              </form>

              <p className="mt-4 text-center text-[11px] text-muted">
                <Link href="/terms" className="hover:text-ink" onClick={onClose}>Умови</Link>
                {" · "}
                <Link href="/privacy" className="hover:text-ink" onClick={onClose}>Конфіденційність</Link>
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
