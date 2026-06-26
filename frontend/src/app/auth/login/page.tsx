"use client";

import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { IconMail, IconLock, IconEye } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError, auth as authApi } from "@/lib/api";
import { getRememberMePreference, getSavedEmail } from "@/lib/auth-storage";
import { CodeInput } from "@/components/auth/CodeInput";

const HERO_IMAGE = "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1200&q=80";
const TESTIMONIAL_AVATAR =
  "https://media.istockphoto.com/id/1485546774/uk/%D1%84%D0%BE%D1%82%D0%BE/%D0%BB%D0%B8%D1%81%D0%B8%D0%B9-%D1%87%D0%BE%D0%BB%D0%BE%D0%B2%D1%96%D0%BA-%D0%BF%D0%BE%D1%81%D0%BC%D1%96%D1%85%D0%B0%D1%94%D1%82%D1%8C%D1%81%D1%8F-%D0%BD%D0%B0-%D0%BA%D0%B0%D0%BC%D0%B5%D1%80%D1%83-%D1%81%D1%82%D0%BE%D1%8F%D1%87%D0%B8-%D0%B7%D1%96-%D1%81%D1%85%D1%80%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D0%BC%D0%B8-%D1%80%D1%83%D0%BA%D0%B0%D0%BC%D0%B8.jpg?s=612x612&w=0&k=20&c=k8rWF64vFG376FAR8UmfKKEjqXvLkAGM4FRbucNTgUw=";

type Tab = "login" | "register";
type RegisterStep = "form" | "verify";
type LoginStep = "form" | "forgot";

function GoogleLogo({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
      <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1Z" fill="#4285F4"/>
      <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23Z" fill="#34A853"/>
      <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62Z" fill="#FBBC05"/>
      <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53Z" fill="#EA4335"/>
    </svg>
  );
}

function TelegramLogo({ size = 20 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
      <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm4.64 6.8c-.15 1.58-.8 5.42-1.13 7.19-.14.75-.42 1-.68 1.03-.58.05-1.02-.38-1.58-.75-.88-.58-1.38-.94-2.23-1.5-.99-.65-.35-1.01.22-1.59.15-.15 2.71-2.48 2.76-2.69a.2.2 0 0 0-.05-.18c-.06-.05-.14-.03-.21-.02-.09.02-1.49.95-4.22 2.79-.4.27-.76.41-1.08.4-.36-.01-1.04-.2-1.55-.37-.63-.2-1.12-.31-1.08-.66.02-.18.27-.36.74-.55 2.92-1.27 4.86-2.11 5.83-2.51 2.78-1.16 3.35-1.36 3.73-1.36.08 0 .27.02.39.12.1.08.13.19.14.27-.01.06.01.24 0 .38z"/>
    </svg>
  );
}

function SocialButton({
  provider,
  disabled,
  onClick,
}: {
  provider: "google" | "telegram";
  disabled?: boolean;
  onClick: () => void;
}) {
  if (provider === "google") {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={onClick}
        className="group flex-1 min-w-0 min-h-[60px] rounded-xl bg-white border border-[#747775] hover:border-[#1f1f1f]/30 hover:shadow-sm transition-all flex flex-col items-center justify-center gap-1.5 px-2 py-2.5 text-[#1f1f1f] disabled:opacity-50"
      >
        <GoogleLogo size={20} />
        <span className="text-[10px] sm:text-[11px] font-medium leading-tight text-center">Google</span>
      </button>
    );
  }

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className="group flex-1 min-w-0 min-h-[60px] rounded-xl bg-[#2481cc] hover:bg-[#1d6fad] text-white flex flex-col items-center justify-center gap-1.5 px-2 py-2.5 transition-colors disabled:opacity-50"
    >
      <TelegramLogo size={20} />
      <span className="text-[10px] sm:text-[11px] font-medium leading-tight text-center">Telegram</span>
    </button>
  );
}

function AuthForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { login, sendRegisterCode, verifyRegisterCode, resendRegisterCode, forgotPassword } = useAuth();

  const [tab, setTab] = useState<Tab>("login");
  const [registerStep, setRegisterStep] = useState<RegisterStep>("form");
  const [loginStep, setLoginStep] = useState<LoginStep>("form");
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
    setRememberMe(getRememberMePreference());
    const savedEmail = getSavedEmail();
    if (savedEmail) setEmail(savedEmail);
  }, []);

  const redirect = searchParams.get("redirect");
  const plan = searchParams.get("plan");
  const destination = redirect?.startsWith("/app") ? redirect : "/app/dashboard";

  const handleTabChange = (next: Tab) => {
    setTab(next);
    setRegisterStep("form");
    setLoginStep("form");
    setCode("");
    setError("");
    setSuccess("");
  };

  const startResendCooldown = () => {
    setResendCooldown(60);
    const interval = setInterval(() => {
      setResendCooldown(prev => {
        if (prev <= 1) { clearInterval(interval); return 0; }
        return prev - 1;
      });
    }, 1000);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (tab === "register" && password.length < 8) {
      setError("Пароль має містити щонайменше 8 символів");
      return;
    }

    setLoading(true);
    try {
      if (tab === "login") {
        await login(email.trim(), password, rememberMe);
        router.push(destination);
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
    setError("");
    if (code.length !== 6) {
      setError("Введіть 6-значний код");
      return;
    }
    setLoading(true);
    try {
      await verifyRegisterCode(email.trim(), code);
      router.push("/app/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Помилка підтвердження");
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    if (resendCooldown > 0) return;
    setError("");
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

  const handleForgotSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await forgotPassword(email.trim());
      setSuccess("Якщо акаунт існує, ми надіслали лист з інструкціями");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося надіслати лист");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = () => {
    window.location.href = authApi.googleLoginUrl();
  };

  const handleTelegramAuth = async () => {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      const { bot_url } =
        tab === "register"
          ? await authApi.telegramRegisterUrl()
          : await authApi.telegramLoginUrl();
      window.open(bot_url, "_blank", "noopener,noreferrer");
      setSuccess(
        tab === "register"
          ? "Відкрийте Telegram і натисніть «Відкрити кабінет»"
          : "Відкрийте Telegram і натисніть «Увійти в кабінет»",
      );
    } catch (err) {
      setError(
        err instanceof ApiError && err.status === 503
          ? "Telegram-бот не налаштовано. Перевірте TELEGRAM_BOT_USERNAME у .env і перезапустіть backend"
          : err instanceof ApiError
            ? err.message
            : "Не вдалося відкрити Telegram",
      );
    } finally {
      setLoading(false);
    }
  };

  if (tab === "login" && loginStep === "forgot") {
    return (
      <div className="w-full max-w-[420px]">
        <div className="lg:hidden mb-6">
          <Link href="/" className="inline-flex items-center gap-3">
            <span className="w-10 h-10 rounded-full bg-emerald-light ring-1 ring-emerald/20 flex items-center justify-center">
              <LogoIcon size={22} />
            </span>
            <span className="text-[17px] font-bold tracking-tight text-ink">Carbit</span>
          </Link>
        </div>

        <div className="bg-white rounded-[1.5rem] border border-border/60 shadow-card p-6 sm:p-7">
          <button
            type="button"
            onClick={() => { setLoginStep("form"); setError(""); setSuccess(""); }}
            className="text-[13px] text-muted hover:text-ink mb-4 transition-colors"
          >
            ← Назад до входу
          </button>

          <h1 className="text-[28px] font-black tracking-[-0.03em] text-ink leading-none">
            Скидання пароля
          </h1>
          <p className="mt-2 text-[14px] text-muted leading-relaxed">
            Введіть email — надішлемо посилання для встановлення нового пароля
          </p>

          <form onSubmit={handleForgotSubmit} className="mt-6 space-y-4">
            <Field label="Email">
              <div className="auth-input-wrap">
                <IconMail size={18} className="text-muted shrink-0" />
                <input
                  type="email"
                  placeholder="vasyl@example.com"
                  className="auth-input-inner"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                />
              </div>
            </Field>

            {success && (
              <p className="text-[13px] text-emerald-dark bg-emerald-light/50 border border-emerald/20 rounded-lg px-3 py-2">
                {success}
              </p>
            )}
            {error && (
              <p className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </p>
            )}

            <Button type="submit" loading={loading} size="md" variant="emerald" showArrow className="w-full">
              Надіслати лист
            </Button>
          </form>
        </div>
      </div>
    );
  }

  if (tab === "register" && registerStep === "verify") {
    return (
      <div className="w-full max-w-[420px]">
        <div className="lg:hidden mb-6">
          <Link href="/" className="inline-flex items-center gap-3">
            <span className="w-10 h-10 rounded-full bg-emerald-light ring-1 ring-emerald/20 flex items-center justify-center">
              <LogoIcon size={22} />
            </span>
            <span className="text-[17px] font-bold tracking-tight text-ink">Carbit</span>
          </Link>
        </div>

        <div className="bg-white rounded-[1.5rem] border border-border/60 shadow-card p-6 sm:p-7">
          <button
            type="button"
            onClick={() => { setRegisterStep("form"); setCode(""); setError(""); }}
            className="text-[13px] text-muted hover:text-ink mb-4 transition-colors"
          >
            ← Назад
          </button>

          <h1 className="text-[28px] font-black tracking-[-0.03em] text-ink leading-none">
            Підтвердіть email
          </h1>
          <p className="mt-2 text-[14px] text-muted leading-relaxed">
            Ми надіслали 6-значний код на{" "}
            <strong className="text-ink">{email}</strong>
          </p>

          <form onSubmit={handleVerify} className="mt-8 space-y-6">
            <CodeInput value={code} onChange={setCode} disabled={loading} />

            {success && (
              <p className="text-[13px] text-emerald-dark bg-emerald-light/50 border border-emerald/20 rounded-lg px-3 py-2 text-center">
                {success}
              </p>
            )}
            {error && (
              <p className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2 text-center">
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
              disabled={code.length !== 6}
            >
              Підтвердити
            </Button>

            <p className="text-center text-[13px] text-muted">
              Не отримали код?{" "}
              <button
                type="button"
                onClick={handleResend}
                disabled={resendCooldown > 0 || loading}
                className={cn(
                  "font-semibold transition-colors",
                  resendCooldown > 0 ? "text-muted cursor-not-allowed" : "text-emerald-dark hover:underline",
                )}
              >
                {resendCooldown > 0 ? `Повторити через ${resendCooldown}с` : "Надіслати знову"}
              </button>
            </p>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[420px]">
      <div className="lg:hidden mb-6">
        <Link href="/" className="inline-flex items-center gap-3">
          <span className="w-10 h-10 rounded-full bg-emerald-light ring-1 ring-emerald/20 flex items-center justify-center">
            <LogoIcon size={22} />
          </span>
          <span className="text-[17px] font-bold tracking-tight text-ink">Carbit</span>
        </Link>
      </div>

      <div className="bg-white rounded-[1.5rem] border border-border/60 shadow-card p-6 sm:p-7">
        <h1 className="text-[30px] sm:text-[34px] font-black tracking-[-0.03em] text-ink leading-none">
          {tab === "login" ? "З поверненням" : "Реєстрація"}
        </h1>
        <p className="mt-2 text-[14px] text-muted">
          {tab === "login"
            ? "Увійдіть до кабінету або створіть акаунт"
            : plan
              ? `7 днів безкоштовно на тарифі ${plan.toUpperCase()}`
              : "7 днів безкоштовно, без карти"}
        </p>

        <div className="mt-5 flex bg-surface rounded-full p-1 border border-border/60">
          {(["login", "register"] as Tab[]).map(t => (
            <button
              key={t}
              type="button"
              onClick={() => handleTabChange(t)}
              className={cn(
                "flex-1 py-2 text-[14px] font-semibold rounded-full transition-all duration-200",
                tab === t ? "bg-ink text-white shadow-md" : "text-muted hover:text-ink"
              )}
            >
              {t === "login" ? "Вхід" : "Реєстрація"}
            </button>
          ))}
        </div>

        <form onSubmit={handleSubmit} className="mt-5 space-y-3.5">
          {tab === "register" && (
            <Field label="Ім'я">
              <input
                type="text"
                placeholder="Василь"
                className="auth-input"
                value={name}
                onChange={e => setName(e.target.value)}
                required
                autoComplete="name"
              />
            </Field>
          )}
          <Field label="Email">
            <div className="auth-input-wrap">
              <IconMail size={18} className="text-muted shrink-0" />
              <input
                type="email"
                placeholder="vasyl@example.com"
                className="auth-input-inner"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </div>
          </Field>
          <Field label="Пароль">
            <div className="auth-input-wrap">
              <IconLock size={18} className="text-muted shrink-0" />
              <input
                type={showPass ? "text" : "password"}
                placeholder="Мінімум 8 символів"
                className="auth-input-inner"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={tab === "register" ? 8 : 1}
                autoComplete={tab === "login" ? "current-password" : "new-password"}
              />
              <button
                type="button"
                onClick={() => setShowPass(!showPass)}
                className="text-muted hover:text-ink transition-colors p-1"
                aria-label={showPass ? "Сховати пароль" : "Показати пароль"}
              >
                <IconEye size={18} />
              </button>
            </div>
          </Field>

          {success && (
            <p className="text-[13px] text-emerald-dark bg-emerald-light/50 border border-emerald/20 rounded-lg px-3 py-2">
              {success}
            </p>
          )}

          {error && (
            <p className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
              {error}
            </p>
          )}

          {tab === "login" && (
            <div className="flex items-center justify-between gap-3 -mt-1">
              <label className="flex cursor-pointer select-none items-center gap-2.5">
                <input
                  type="checkbox"
                  checked={rememberMe}
                  onChange={e => setRememberMe(e.target.checked)}
                  className="h-4 w-4 rounded border-border text-emerald accent-emerald focus:ring-emerald/30"
                />
                <span className="text-[13px] text-muted">Запам&apos;ятати мене</span>
              </label>
              <button
                type="button"
                onClick={() => { setLoginStep("forgot"); setError(""); setSuccess(""); }}
                className="text-[13px] font-medium text-emerald-dark hover:underline shrink-0"
              >
                Забули пароль?
              </button>
            </div>
          )}

          <Button
            type="submit"
            loading={loading}
            size="md"
            variant="emerald"
            showArrow
            className="w-full"
          >
            {tab === "login" ? "Увійти" : "Продовжити"}
          </Button>

          <div className="flex items-center gap-3">
            <span className="flex-1 h-px bg-border" />
            <span className="text-[12px] text-muted font-medium">або</span>
            <span className="flex-1 h-px bg-border" />
          </div>

          <div className="flex items-center gap-2.5">
            <SocialButton provider="google" disabled={loading} onClick={handleGoogleLogin} />
            <SocialButton provider="telegram" disabled={loading} onClick={handleTelegramAuth} />
          </div>
        </form>
      </div>

      <p className="mt-5 text-center text-[12px] text-muted leading-relaxed px-4">
        Продовжуючи, ви приймаєте{" "}
        <Link href="/terms" className="text-ink font-medium hover:text-emerald-dark transition-colors">
          Умови
        </Link>{" "}
        та{" "}
        <Link href="/privacy" className="text-ink font-medium hover:text-emerald-dark transition-colors">
          Політику конфіденційності
        </Link>
      </p>
    </div>
  );
}

export default function AuthPage() {
  return (
    <div className="min-h-screen bg-white flex">
      <div className="hidden lg:flex w-[520px] xl:w-[560px] shrink-0 relative overflow-hidden">
        <Image
          src={HERO_IMAGE}
          alt=""
          fill
          className="object-cover"
          sizes="560px"
          priority
        />
        <div className="absolute inset-0 bg-gradient-to-br from-ink/95 via-ink/85 to-ink/70" />
        <div className="absolute top-1/3 right-0 w-64 h-64 bg-emerald/20 rounded-full blur-[100px] pointer-events-none" />

        <div className="relative z-10 flex flex-col justify-between p-12 xl:p-14 w-full">
          <Link href="/" className="flex items-center gap-3 group w-fit">
            <span className="w-11 h-11 rounded-full bg-white/10 ring-1 ring-white/20 flex items-center justify-center group-hover:scale-105 transition-transform">
              <LogoIcon size={24} light />
            </span>
            <span className="text-white text-[18px] font-bold tracking-tight">Carbit</span>
          </Link>

          <div className="rounded-3xl bg-white/10 backdrop-blur-xl border border-white/15 p-8">
            <blockquote className="text-[26px] font-bold text-white leading-snug tracking-tight">
              «Знайшов авто за 40 хв після реєстрації. Конкурент запізнився на 2 години.»
            </blockquote>
            <div className="mt-7 flex items-center gap-4">
              <div className="relative h-11 w-11 shrink-0 overflow-hidden rounded-full ring-2 ring-white/20 shadow-lg">
                <Image
                  src={TESTIMONIAL_AVATAR}
                  alt="Василь К."
                  fill
                  className="object-cover"
                  sizes="44px"
                />
              </div>
              <div>
                <div className="text-white text-[15px] font-semibold">Василь К.</div>
                <div className="text-white/50 text-[13px]">Перекупник · Київ</div>
              </div>
            </div>
            <div className="mt-8 grid grid-cols-3 gap-4 pt-8 border-t border-white/10">
              {[["1 200+", "оголошень/день"], ["< 5 хв", "до сповіщення"], ["72%", "платять"]].map(([v, l]) => (
                <div key={l}>
                  <div className="text-[24px] font-black text-emerald">{v}</div>
                  <div className="text-[12px] text-white/45 mt-1 leading-tight">{l}</div>
                </div>
              ))}
            </div>
          </div>

          <p className="text-[13px] text-white/30">© 2026 Carbit</p>
        </div>
      </div>

      <div className="flex-1 flex items-center justify-center px-6 sm:px-8 py-8 bg-white">
        <Suspense fallback={<div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />}>
          <AuthForm />
        </Suspense>
      </div>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-[12px] font-semibold text-ink mb-1">{label}</label>
      {children}
    </div>
  );
}
