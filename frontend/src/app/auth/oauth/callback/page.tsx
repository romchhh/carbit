"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { useAuth } from "@/contexts/AuthProvider";

const ERROR_MESSAGES: Record<string, string> = {
  access_denied: "Вхід через Google скасовано",
  invalid_state: "Невалідна сесія. Спробуйте ще раз",
  oauth_failed: "Не вдалося авторизуватись через Google",
  profile_incomplete: "Google не надав email. Спробуйте інший акаунт",
  account_deactivated: "Акаунт деактивовано",
};

function OAuthCallback() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { loginWithToken } = useAuth();
  const [error, setError] = useState("");

  useEffect(() => {
    const token = searchParams.get("token");
    const err = searchParams.get("error");

    if (err) {
      setError(ERROR_MESSAGES[err] ?? "Помилка авторизації");
      return;
    }

    if (!token) {
      setError("Токен не отримано");
      return;
    }

    loginWithToken(token)
      .then(() => router.replace("/app/dashboard"))
      .catch(() => setError("Не вдалося завершити вхід"));
  }, [searchParams, loginWithToken, router]);

  if (error) {
    return (
      <div className="text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Link href="/auth/login"><Button variant="secondary" size="md">Спробувати знову</Button></Link>
      </div>
    );
  }

  return (
    <div className="flex justify-center py-12">
      <div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin" />
    </div>
  );
}

export default function OAuthCallbackPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center p-6">
      <div className="w-full max-w-[400px] bg-white rounded-[1.5rem] border border-border/60 shadow-card p-7">
        <Suspense fallback={<div className="w-8 h-8 border-2 border-emerald border-t-transparent rounded-full animate-spin mx-auto" />}>
          <OAuthCallback />
        </Suspense>
      </div>
    </div>
  );
}
