"use client";

import { useCallback, useEffect, useState } from "react";
import { adminApi, AdminApiError, type AdminTelethonSessionStatus } from "@/lib/admin-api";
import { cn } from "@/lib/utils";

type Props = {
  onMessage: (text: string | null) => void;
  workerOnline?: boolean;
};

export function TelethonSessionPanel({ onMessage, workerOnline }: Props) {
  const [status, setStatus] = useState<AdminTelethonSessionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [code, setCode] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.telethonSessionStatus();
      setStatus(data);
    } catch {
      setStatus(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const run = async (label: string, fn: () => Promise<void>) => {
    setBusy(label);
    onMessage(null);
    try {
      await fn();
    } catch (err) {
      onMessage(err instanceof AdminApiError ? err.message : "Помилка");
    } finally {
      setBusy(null);
    }
  };

  const needsPassword = status?.auth_step === "password";

  return (
    <section className="mb-6 rounded-2xl border border-amber-200/80 bg-amber-50/40 p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-[16px] font-bold text-ink">Telethon-сесія (парсер каналів)</h2>
          <p className="mt-1 max-w-xl text-[12px] text-muted">
            Один акаунт Telegram — один файл сесії на сервері. Перед скиданням/новим кодом зупиніть{" "}
            <code className="text-[11px]">telegram-worker</code>, і не запускайте{" "}
            <code className="text-[11px]">auth.py</code> локально з тим самим .session.
          </p>
        </div>
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="text-[12px] font-semibold text-emerald hover:underline disabled:opacity-60"
        >
          Оновити
        </button>
      </div>

      {workerOnline && (
        <p className="mt-3 rounded-lg border border-amber-300/60 bg-white/80 px-3 py-2 text-[12px] text-amber-900">
          Worker зараз online — для безпечного оновлення сесії краще{" "}
          <span className="font-semibold">docker compose stop telegram-worker</span>, потім увійти тут і знову
          запустити worker.
        </p>
      )}

      {loading && !status ? (
        <div className="mt-4 flex justify-center py-6">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      ) : status ? (
        <div className="mt-4 space-y-3">
          <div className="grid gap-2 text-[12px] sm:grid-cols-2">
            <div>
              <span className="text-muted">Файл: </span>
              <span className="font-mono text-[11px] text-ink">{status.session_file}</span>
            </div>
            <div>
              <span className="text-muted">Телефон (.env): </span>
              <span className="text-ink">{status.phone_masked}</span>
            </div>
            <div>
              <span className="text-muted">Статус: </span>
              <span
                className={cn(
                  "font-semibold",
                  status.authorized ? "text-emerald-dark" : "text-amber-800",
                )}
              >
                {status.authorized
                  ? status.user?.username
                    ? `@${status.user.username}`
                    : status.user?.first_name || "Авторизовано"
                  : status.session_exists
                    ? "Не авторизовано / сесія недійсна"
                    : "Немає файлу сесії"}
              </span>
            </div>
          </div>

          {status.session_note && status.authorized && (
            <div className="rounded-xl border border-emerald/30 bg-emerald-light/30 px-3 py-2 text-[12px] text-emerald-dark">
              {status.session_note}
            </div>
          )}

          {status.error && !status.authorized && (
            <div className="rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-[12px] text-red-800">
              {status.error}
            </div>
          )}

          <div className="flex flex-wrap gap-2 border-t border-amber-200/60 pt-4">
            <button
              type="button"
              disabled={busy !== null || !status.phone_configured}
              onClick={() =>
                void run("send", async () => {
                  const res = await adminApi.telethonSendCode();
                  if (res.status === "already_authorized") {
                    onMessage("Вже авторизовано");
                  } else {
                    onMessage(`Код надіслано на ${res.phone_masked ?? "номер"}`);
                  }
                  await load();
                })
              }
              className="rounded-full bg-emerald px-4 py-2 text-[12px] font-semibold text-white hover:bg-emerald-dark disabled:opacity-60"
            >
              {busy === "send" ? "…" : "Надіслати код"}
            </button>
            <button
              type="button"
              disabled={busy !== null}
              onClick={() =>
                void run("reset", async () => {
                  if (
                    !window.confirm(
                      "Видалити файли сесії на сервері? Потім потрібен новий вхід кодом.",
                    )
                  ) {
                    return;
                  }
                  const res = await adminApi.telethonResetSession();
                  onMessage(
                    res.removed.length
                      ? `Сесію скинуто (${res.removed.length} файлів)`
                      : "Файлів сесії не було",
                  );
                  setCode("");
                  setPassword("");
                  await load();
                })
              }
              className="rounded-full border border-red-300 px-4 py-2 text-[12px] font-semibold text-red-700 hover:bg-red-50 disabled:opacity-60"
            >
              {busy === "reset" ? "…" : "Скинути сесію"}
            </button>
          </div>

          {!status.authorized && (
            <div className="flex flex-wrap items-end gap-3">
              {!needsPassword ? (
                <>
                  <label className="min-w-[160px] text-[12px] font-semibold text-muted">
                    Код з SMS / Telegram
                    <input
                      value={code}
                      onChange={e => setCode(e.target.value.replace(/\D/g, "").slice(0, 8))}
                      placeholder="12345"
                      className="mt-1.5 w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-[14px] text-ink outline-none focus:border-emerald"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={busy !== null || code.length < 4}
                    onClick={() =>
                      void run("code", async () => {
                        const res = await adminApi.telethonSignIn(code);
                        if (res.status === "password_required") {
                          onMessage("Потрібен пароль 2FA");
                        } else {
                          onMessage("Telethon авторизовано");
                          setCode("");
                        }
                        await load();
                      })
                    }
                    className="rounded-full border border-border/80 px-4 py-2.5 text-[12px] font-semibold text-ink hover:bg-white disabled:opacity-60"
                  >
                    {busy === "code" ? "…" : "Підтвердити код"}
                  </button>
                </>
              ) : (
                <>
                  <label className="min-w-[160px] text-[12px] font-semibold text-muted">
                    Пароль 2FA
                    <input
                      type="password"
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      className="mt-1.5 w-full rounded-xl border border-border/80 bg-white px-3 py-2 text-[14px] text-ink outline-none focus:border-emerald"
                    />
                  </label>
                  <button
                    type="button"
                    disabled={busy !== null || !password.trim()}
                    onClick={() =>
                      void run("pw", async () => {
                        await adminApi.telethonPassword(password);
                        onMessage("Telethon авторизовано (2FA)");
                        setPassword("");
                        await load();
                      })
                    }
                    className="rounded-full border border-border/80 px-4 py-2.5 text-[12px] font-semibold text-ink hover:bg-white disabled:opacity-60"
                  >
                    {busy === "pw" ? "…" : "Увійти з 2FA"}
                  </button>
                </>
              )}
            </div>
          )}
        </div>
      ) : null}
    </section>
  );
}
