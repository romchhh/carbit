"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { auth as authApi, ApiError } from "@/lib/api";
import { setToken } from "@/lib/auth-storage";

function TelegramLoginForm() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token") ?? "";
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;

    authApi.telegramLogin(token)
      .then(({ access_token }) => {
        setToken(access_token);
        router.replace("/app/dashboard");
      })
      .catch(err => {
        setError(err instanceof ApiError ? err.message : "Не вдалося увійти");
      });
  }, [token, router]);

  if (!token) {
    return (
      <div className="text-center">
        <p className="text-muted mb-4">Невірне посилання. Отримайте нове в Telegram-боті.</p>
        <Link href="/auth/login"><Button variant="secondary" size="md">На сторінку входу</Button></Link>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Link href="/auth/login"><Button variant="secondary" size="md">Увійти іншим способом</Button></Link>
      </div>
    );
  }

  return (
    <div className="text-center py-8">
      <div className="w-14 h-14 rounded-full bg-emerald-light mx-auto mb-4 flex items-center justify-center">
        <LogoIcon size={28} />
      </div>
      <p className="text-[15px] text-muted">Вхід через Telegram...</p>
      <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin mx-auto mt-6" />
    </div>
  );
}

export default function TelegramLoginPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="w-full max-w-[400px] bg-white rounded-[1.5rem] border border-border/60 shadow-card p-7">
        <Suspense fallback={<div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin mx-auto" />}>
          <TelegramLoginForm />
        </Suspense>
      </div>
    </div>
  );
}
