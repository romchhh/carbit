"use client";

import { Suspense, useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { CarbitLogo } from "@/components/brand/CarbitLogo";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError } from "@/lib/api";
import { resolvePostAuthRedirect } from "@/lib/search-draft";
import { CodeInput } from "@/components/auth/CodeInput";
import { PhoneInput, normalizePhoneForApi } from "@/components/auth/PhoneInput";

const HERO_IMAGE = "https://images.unsplash.com/photo-1492144534655-ae79c964c9d7?auto=format&fit=crop&w=1200&q=80";
const TESTIMONIAL_AVATAR =
  "https://media.istockphoto.com/id/1485546774/uk/%D1%84%D0%BE%D1%82%D0%BE/%D0%BB%D0%B8%D1%81%D0%B8%D0%B9-%D1%87%D0%BE%D0%BB%D0%BE%D0%B2%D1%96%D0%BA-%D0%BF%D0%BE%D1%81%D0%BC%D1%96%D1%85%D0%B0%D1%94%D1%82%D1%8C%D1%81%D1%8F-%D0%BD%D0%B0-%D0%BA%D0%B0%D0%BC%D0%B5%D1%80%D1%83-%D1%81%D1%82%D0%BE%D1%8F%D1%87%D0%B8-%D0%B7%D1%96-%D1%81%D1%85%D1%80%D0%B5%D1%89%D0%B5%D0%BD%D0%B8%D0%BC%D0%B8-%D1%80%D1%83%D0%BA%D0%B0%D0%BC%D0%B8.jpg?s=612x612&w=0&k=20&c=k8rWF64vFG376FAR8UmfKKEjqXvLkAGM4FRbucNTgUw=";

type Tab = "login" | "register";
type PhoneStep = "form" | "verify";
type LoginMethod = "code" | "password";
type CodeChannel = "sms" | "telegram";

function AuthForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { sendPhoneCode, verifyPhoneCode, phoneLogin, user, loading: authLoading, initialized } = useAuth();

  const [tab, setTab] = useState<Tab>("login");
  const [loginMethod, setLoginMethod] = useState<LoginMethod>("code");
  const [phoneStep, setPhoneStep] = useState<PhoneStep>("form");
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [phone, setPhone] = useState("");
  const [phoneCode, setPhoneCode] = useState("");
  const [phoneName, setPhoneName] = useState("");
  const [password, setPassword] = useState("");
  const [codeChannel, setCodeChannel] = useState<CodeChannel>("sms");

  const redirect = searchParams.get("redirect");
  const destination = resolvePostAuthRedirect(redirect);

  useEffect(() => {
    if (!initialized || authLoading || !user) return;
    router.replace(destination);
  }, [initialized, authLoading, user, router, destination]);

  useEffect(() => {
    const tabParam = searchParams.get("tab");
    const sessionParam = searchParams.get("session");

    if (sessionParam === "revoked" || sessionStorage.getItem("carbit_session_revoked") === "1") {
      setError("Ви увійшли з іншого пристрою. Безкоштовний тариф дозволяє 1 активну сесію — увійдіть знову.");
      sessionStorage.removeItem("carbit_session_revoked");
    }

    if (tabParam === "register") setTab("register");
  }, [searchParams]);

  const handleTabChange = (next: Tab) => {
    setTab(next);
    setPhoneStep("form");
    setLoginMethod("code");
    setPhoneCode("");
    setPassword("");
    setError("");
    setSuccess("");
    setCodeChannel("sms");
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

    setError("");
    setSuccess("");
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
    setError("");
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
      router.replace(
        tab === "register"
          ? "/app/account?setPassword=1"
          : resolvePostAuthRedirect(redirect),
      );
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Помилка підтвердження");
    } finally {
      setLoading(false);
    }
  };

  const handlePhonePasswordLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    const normalized = normalizePhoneForApi(phone);
    if (normalized.length < 12) {
      setError("Введіть повний номер телефону");
      return;
    }
    if (!password) {
      setError("Введіть пароль");
      return;
    }
    setError("");
    setLoading(true);
    try {
      await phoneLogin(normalized, password, true);
      router.replace(resolvePostAuthRedirect(redirect));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Невірний номер або пароль");
    } finally {
      setLoading(false);
    }
  };

  const handlePhoneResend = async (delivery: "auto" | "sms" = "auto") => {
    if (resendCooldown > 0) return;
    await requestCode(delivery);
  };

  if (phoneStep === "verify") {
    const displayPhone = phone ? `+380 ${phone}` : "";
    const channelHint =
      codeChannel === "telegram"
        ? "Код надіслано в Telegram, привʼязаний до вашого акаунта."
        : tab === "register"
          ? `Код надіслано SMS на ${displayPhone}`
          : `Код надіслано SMS на ${displayPhone}`;

    return (
      <div className="w-full max-w-[420px]">
        <div className="lg:hidden mb-6">
          <Link href="/" className="inline-flex items-center">
            <CarbitLogo variant="full" height={32} />
          </Link>
        </div>

        <div className="bg-white rounded-[1.5rem] border border-border/60 shadow-card p-6 sm:p-7">
          <button
            type="button"
            onClick={() => {
              setPhoneStep("form");
              setPhoneCode("");
              setError("");
              setSuccess("");
            }}
            className="text-[13px] text-muted hover:text-ink mb-4 transition-colors"
          >
            ← Назад
          </button>

          <h1 className="text-[28px] font-black tracking-[-0.03em] text-ink leading-none">
            Підтвердіть номер
          </h1>
          <p className="mt-2 text-[14px] text-muted leading-relaxed">{channelHint}</p>

          <form onSubmit={handlePhoneVerify} className="mt-8 space-y-6">
            <CodeInput value={phoneCode} onChange={setPhoneCode} disabled={loading} />

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
              disabled={phoneCode.length !== 6}
            >
              {tab === "login" ? "Увійти" : "Створити акаунт"}
            </Button>

            <div className="space-y-2 text-center text-[13px] text-muted">
              <p>
                Не отримали код?{" "}
                <button
                  type="button"
                  onClick={() => void handlePhoneResend("auto")}
                  disabled={resendCooldown > 0 || loading}
                  className={cn(
                    "font-semibold transition-colors",
                    resendCooldown > 0 ? "text-muted cursor-not-allowed" : "text-emerald-dark hover:underline",
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
                      "font-semibold transition-colors",
                      resendCooldown > 0 ? "text-muted cursor-not-allowed" : "text-emerald-dark hover:underline",
                    )}
                  >
                    Надіслати SMS
                  </button>
                </p>
              )}
            </div>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-[420px]">
      <div className="lg:hidden mb-6">
        <Link href="/" className="inline-flex items-center">
          <CarbitLogo variant="full" height={32} />
        </Link>
      </div>

      <div className="bg-white rounded-[1.5rem] border border-border/60 shadow-card p-6 sm:p-7">
        <div className="flex bg-surface rounded-full p-1 border border-border/60">
          {(["login", "register"] as Tab[]).map(t => (
            <button
              key={t}
              type="button"
              onClick={() => handleTabChange(t)}
              className={cn(
                "flex-1 py-2.5 text-[14px] font-semibold rounded-full transition-all duration-200",
                tab === t ? "bg-ink text-white shadow-md" : "text-muted hover:text-ink",
              )}
            >
              {t === "login" ? "Вхід" : "Реєстрація"}
            </button>
          ))}
        </div>

        <p className="mt-5 text-[14px] text-muted leading-relaxed">
          {tab === "login"
            ? loginMethod === "password"
              ? "Вхід за номером телефону та паролем — без SMS-коду."
              : "Введіть номер телефону. Код надішлемо в Telegram, якщо він привʼязаний, інакше — SMS."
            : "Введіть імʼя та номер. Код підтвердження надішлемо SMS."}
        </p>

        {tab === "login" && (
          <div className="mt-4 flex rounded-full border border-border/60 bg-surface p-0.5 text-[12px] font-semibold">
            <button
              type="button"
              onClick={() => {
                setLoginMethod("code");
                setError("");
              }}
              className={cn(
                "flex-1 rounded-full py-2 transition-colors",
                loginMethod === "code" ? "bg-white text-ink shadow-sm" : "text-muted",
              )}
            >
              Код SMS / Telegram
            </button>
            <button
              type="button"
              onClick={() => {
                setLoginMethod("password");
                setError("");
              }}
              className={cn(
                "flex-1 rounded-full py-2 transition-colors",
                loginMethod === "password" ? "bg-white text-ink shadow-sm" : "text-muted",
              )}
            >
              Пароль
            </button>
          </div>
        )}

        {tab === "login" && loginMethod === "password" ? (
          <form onSubmit={handlePhonePasswordLogin} className="mt-4 space-y-3">
            <PhoneInput value={phone} onChange={setPhone} disabled={loading} />
            <input
              type="password"
              placeholder="Пароль"
              className="auth-input w-full"
              value={password}
              onChange={e => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
            {error && (
              <p className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">
                {error}
              </p>
            )}
            <Button type="submit" loading={loading} size="md" variant="emerald" showArrow className="w-full">
              Увійти
            </Button>
            <p className="text-[11px] text-center text-muted">
              Немає пароля?{" "}
              <button
                type="button"
                className="font-semibold text-emerald-dark hover:underline"
                onClick={() => setLoginMethod("code")}
              >
                Увійти за кодом
              </button>
            </p>
          </form>
        ) : (
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
            {tab === "login" ? "Отримати код" : "Надіслати код SMS"}
          </Button>
          {tab === "login" && (
            <p className="text-[11px] text-center text-muted">
              Є пароль?{" "}
              <button
                type="button"
                className="font-semibold text-emerald-dark hover:underline"
                onClick={() => setLoginMethod("password")}
              >
                Увійти з паролем
              </button>
            </p>
          )}
        </form>
        )}
      </div>

      <p className="mt-4 text-center text-[11px] text-muted">
        <Link href="/terms" className="hover:text-ink">
          Умови
        </Link>
        {" · "}
        <Link href="/privacy" className="hover:text-ink">
          Конфіденційність
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
          <Link href="/" className="flex items-center group w-fit">
            <CarbitLogo variant="full" height={36} light className="transition-transform group-hover:scale-[1.02]" />
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
              {[["1 500+", "оголошень"], ["< 5 хв", "до сповіщення"], ["7 днів", "безкоштовно"]].map(([v, l]) => (
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
