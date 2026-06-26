"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { telegram as telegramApi, ApiError } from "@/lib/api";
import { useAuth } from "@/contexts/AuthProvider";
import { setToken } from "@/lib/auth-storage";
import { markOnboardingPending } from "@/lib/onboarding";

function TelegramRegisterForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { refreshUser } = useAuth();
  const token = searchParams.get("token") ?? "";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [valid, setValid] = useState(false);
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    telegramApi.registerInfo(token).then(info => {
      setName(info.name);
      setEmail(info.email);
      setValid(info.valid);
    });
  }, [token]);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Пароль має містити щонайменше 8 символів");
      return;
    }
    setLoading(true);
    setError("");
    try {
      const { access_token } = await telegramApi.registerComplete(token, password);
      setToken(access_token);
      await refreshUser();
      markOnboardingPending();
      router.push("/app/onboarding");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Помилка реєстрації");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-muted mb-4">Невірне посилання. Почніть реєстрацію через Telegram-бот.</p>
        <Link href="/auth/login"><Button variant="primary" size="md">На головну</Button></Link>
      </div>
    );
  }

  if (!valid && !name) {
    return (
      <div className="flex justify-center py-12">
        <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  if (!valid) {
    return (
      <div className="text-center">
        <p className="text-red-600 mb-4">Посилання прострочене. Почніть спочатку через бот.</p>
        <Link href="/auth/login"><Button variant="secondary" size="md">Увійти</Button></Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="text-center mb-6">
        <div className="w-14 h-14 rounded-full bg-emerald-light mx-auto mb-4 flex items-center justify-center">
          <LogoIcon size={28} />
        </div>
        <h1 className="text-[24px] font-black text-ink">Майже готово, {name.split(" ")[0]}!</h1>
        <p className="text-[13px] text-muted mt-1">Telegram вже підключено. Встановіть пароль для входу на сайт.</p>
      </div>

      <div className="bg-surface rounded-lg px-3 py-2 text-[13px]">
        <span className="text-muted">Email: </span>
        <span className="text-ink font-medium">{email}</span>
      </div>

      <div>
        <label className="block text-[12px] font-semibold text-ink mb-1">Пароль</label>
        <input
          type="password"
          className="auth-input w-full"
          placeholder="Мінімум 8 символів"
          value={password}
          onChange={e => setPassword(e.target.value)}
          required
          minLength={8}
        />
      </div>

      {error && (
        <p className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
      )}

      <Button type="submit" loading={loading} variant="emerald" size="md" showArrow className="w-full">
        Активувати акаунт
      </Button>
    </form>
  );
}

export default function TelegramAuthPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="w-full max-w-[400px] bg-white rounded-[1.5rem] border border-border/60 shadow-card p-7">
        <Suspense fallback={<div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin mx-auto" />}>
          <TelegramRegisterForm />
        </Suspense>
      </div>
    </div>
  );
}
