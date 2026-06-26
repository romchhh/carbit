"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { IconLock, IconEye } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError } from "@/lib/api";

function ResetForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { resetPassword } = useAuth();
  const token = searchParams.get("token") ?? "";

  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [showPass, setShowPass] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError("Пароль має містити щонайменше 8 символів");
      return;
    }
    if (password !== confirm) {
      setError("Паролі не співпадають");
      return;
    }
    setLoading(true);
    setError("");
    try {
      await resetPassword(token, password);
      router.push("/app/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося змінити пароль");
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-muted mb-4">Невірне посилання для скидання пароля.</p>
        <Link href="/auth/login"><Button variant="secondary" size="md">На сторінку входу</Button></Link>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="space-y-4">
      <div className="text-center mb-2">
        <h1 className="text-[28px] font-black text-ink">Новий пароль</h1>
        <p className="text-[14px] text-muted mt-2">Встановіть новий пароль для входу в кабінет</p>
      </div>

      <div>
        <label className="block text-[12px] font-semibold text-ink mb-1">Новий пароль</label>
        <div className="auth-input-wrap">
          <IconLock size={18} className="text-muted shrink-0" />
          <input
            type={showPass ? "text" : "password"}
            className="auth-input-inner"
            placeholder="Мінімум 8 символів"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            minLength={8}
          />
          <button type="button" onClick={() => setShowPass(!showPass)} className="text-muted hover:text-ink p-1">
            <IconEye size={18} />
          </button>
        </div>
      </div>

      <div>
        <label className="block text-[12px] font-semibold text-ink mb-1">Підтвердження</label>
        <div className="auth-input-wrap">
          <IconLock size={18} className="text-muted shrink-0" />
          <input
            type={showPass ? "text" : "password"}
            className="auth-input-inner"
            placeholder="Повторіть пароль"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            required
            minLength={8}
          />
        </div>
      </div>

      {error && (
        <p className="text-[13px] text-red-600 bg-red-50 border border-red-100 rounded-lg px-3 py-2">{error}</p>
      )}

      <Button type="submit" loading={loading} variant="emerald" size="md" showArrow className="w-full">
        Зберегти пароль
      </Button>
    </form>
  );
}

export default function ResetPasswordPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="w-full max-w-[420px]">
        <div className="mb-6 text-center">
          <Link href="/" className="inline-flex items-center gap-2">
            <span className="w-10 h-10 rounded-full bg-emerald-light ring-1 ring-emerald/20 flex items-center justify-center">
              <LogoIcon size={22} />
            </span>
            <span className="text-[17px] font-bold text-ink">AutoRadar</span>
          </Link>
        </div>
        <div className="bg-white rounded-[1.5rem] border border-border/60 shadow-card p-6 sm:p-7">
          <Suspense fallback={<div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin mx-auto" />}>
            <ResetForm />
          </Suspense>
        </div>
      </div>
    </div>
  );
}
