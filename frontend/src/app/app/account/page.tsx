"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { IconGear, IconCreditCard, IconTelegram, IconArrowRight, IconZap } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError, telegram as telegramApi, billing as billingApi, users as usersApi } from "@/lib/api";
import { CodeInput } from "@/components/auth/CodeInput";
import { PLAN_LABELS } from "@/lib/utils";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { getTelegramBotMention, getTelegramBotUrl } from "@/lib/telegram";
import { AppPage, AppSection } from "@/components/layout/AppPage";
import type { Subscription } from "@/types/api";

export default function AccountPage() {
  const { user, updateProfile, logout, refreshUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [connectUrl, setConnectUrl] = useState<string | null>(null);
  const [tgLoading, setTgLoading] = useState(false);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [polling, setPolling] = useState(false);
  const [bindEmail, setBindEmail] = useState("");
  const [bindCode, setBindCode] = useState("");
  const [bindStep, setBindStep] = useState<"idle" | "code">("idle");
  const [bindLoading, setBindLoading] = useState(false);
  const [bindError, setBindError] = useState("");
  const [bindSuccess, setBindSuccess] = useState("");

  useEffect(() => {
    billingApi.subscription().then(setSubscription).catch(() => {});
  }, [user]);

  const pollTelegramStatus = useCallback(async () => {
    const status = await telegramApi.status();
    if (status.connected) {
      await refreshUser();
      setPolling(false);
      setConnectUrl(null);
    }
  }, [refreshUser]);

  useEffect(() => {
    if (!polling) return;
    const interval = setInterval(pollTelegramStatus, 2000);
    return () => clearInterval(interval);
  }, [polling, pollTelegramStatus]);

  if (!user) return null;

  const planLabel = PLAN_LABELS[user.plan] ?? user.plan;

  const startEdit = () => { setName(user.name); setError(""); setEditing(true); };

  const saveProfile = async () => {
    if (!name.trim()) { setError("Введіть ім'я"); return; }
    setSaving(true);
    try {
      await updateProfile(name.trim());
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти");
    } finally {
      setSaving(false);
    }
  };

  const connectTelegram = async () => {
    setTgLoading(true);
    try {
      const link = await telegramApi.connectLink();
      setConnectUrl(link.bot_url);
      window.open(link.bot_url, "_blank");
      setPolling(true);
    } catch (err) {
      alert(err instanceof ApiError ? err.message : "Помилка");
    } finally {
      setTgLoading(false);
    }
  };

  const disconnectTelegram = async () => {
    if (!confirm("Відключити Telegram-бот?")) return;
    await telegramApi.disconnect();
    await refreshUser();
    setConnectUrl(null);
  };

  const sendBindCode = async () => {
    setBindError("");
    setBindSuccess("");
    if (!bindEmail.trim()) {
      setBindError("Вкажіть email");
      return;
    }
    setBindLoading(true);
    try {
      await usersApi.sendEmailBindCode(bindEmail.trim());
      setBindStep("code");
      setBindSuccess("Код надіслано на пошту");
    } catch (err) {
      setBindError(err instanceof ApiError ? err.message : "Не вдалося надіслати код");
    } finally {
      setBindLoading(false);
    }
  };

  const verifyBindCode = async () => {
    setBindError("");
    setBindSuccess("");
    if (bindCode.length !== 6) {
      setBindError("Введіть 6-значний код");
      return;
    }
    setBindLoading(true);
    try {
      await usersApi.verifyEmailBind(bindEmail.trim(), bindCode);
      await refreshUser();
      setBindStep("idle");
      setBindCode("");
      setBindSuccess("Email підтверджено");
    } catch (err) {
      setBindError(err instanceof ApiError ? err.message : "Невірний код");
    } finally {
      setBindLoading(false);
    }
  };

  return (
    <AppPage title="Акаунт" description="Профіль, тариф і підключення Telegram">
      <div className="space-y-4">
        <AppSection className="!bg-white">
          <div className="flex items-center gap-4">
            <UserAvatar
              name={user.name}
              avatarUrl={user.avatar_url}
              className="h-14 w-14 shrink-0 text-[18px] font-black"
            />
            <div className="min-w-0 flex-1">
              {editing ? (
                <div className="space-y-2">
                  <input type="text" value={name} onChange={e => setName(e.target.value)} className="auth-input w-full" autoFocus />
                  {error && <p className="text-[12px] text-red-600">{error}</p>}
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm" loading={saving} onClick={saveProfile}>Зберегти</Button>
                    <Button variant="secondary" size="sm" onClick={() => setEditing(false)} disabled={saving}>Скасувати</Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="text-[16px] font-bold text-ink">{user.name}</div>
                  <div className="mt-0.5 text-[12px] text-muted">
                    {user.email_verified ? user.email : "Email не вказано"}
                  </div>
                </>
              )}
            </div>
            {!editing && (
              <Button variant="secondary" size="sm" className="shrink-0 gap-1.5" onClick={startEdit}>
                <IconGear size={13} /> Редагувати
              </Button>
            )}
          </div>
        </AppSection>

        <AppSection className="!bg-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted">Тариф</div>
              <div className="mt-1 text-[20px] font-black text-ink">{planLabel}</div>
              {subscription?.is_trial_active && (
                <div className="mt-1 text-[12px] text-emerald-dark">Trial · 3 дні безкоштовно</div>
              )}
            </div>
            <Badge variant="emerald"><IconZap size={10} className="mr-1" />Активний</Badge>
          </div>
          <div className="mt-5 grid grid-cols-3 gap-3">
            {[
              [String(user.searches_limit), "запитів"],
              ["3", "джерела"],
              [user.telegram_connected ? "✓" : "—", "Telegram"],
            ].map(([v, l]) => (
              <div key={l} className="rounded-xl bg-surface px-3 py-3 text-center">
                <div className="text-[18px] font-black text-ink">{v}</div>
                <div className="mt-0.5 text-[11px] text-muted">{l}</div>
              </div>
            ))}
          </div>
          <div className="mt-5 flex flex-wrap gap-3">
            <Link href="/app/billing">
              <Button variant="primary" size="md" className="gap-1.5"><IconCreditCard size={13} /> Підписка</Button>
            </Link>
            <Link href="/pricing"><Button variant="secondary" size="md">Тарифи</Button></Link>
          </div>
        </AppSection>

        {!user.email_verified && (
          <AppSection className="!bg-white">
            <div className="text-[14px] font-semibold text-ink">Email</div>
            <p className="mt-1 text-[12px] text-muted">
              Додайте email для входу через пошту та сповіщень. Потрібне підтвердження кодом.
            </p>
            {bindStep === "idle" ? (
              <div className="mt-4 space-y-3">
                <input
                  type="email"
                  className="auth-input w-full"
                  placeholder="you@example.com"
                  value={bindEmail}
                  onChange={e => setBindEmail(e.target.value)}
                />
                <Button variant="primary" size="sm" loading={bindLoading} onClick={sendBindCode}>
                  Надіслати код
                </Button>
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                <p className="text-[12px] text-muted">Код надіслано на <strong>{bindEmail}</strong></p>
                <CodeInput value={bindCode} onChange={setBindCode} />
                <div className="flex gap-2">
                  <Button variant="primary" size="sm" loading={bindLoading} onClick={verifyBindCode}>
                    Підтвердити
                  </Button>
                  <Button variant="secondary" size="sm" disabled={bindLoading} onClick={() => { setBindStep("idle"); setBindCode(""); setBindError(""); }}>
                    Змінити email
                  </Button>
                </div>
              </div>
            )}
            {bindError && <p className="mt-3 text-[12px] text-red-600">{bindError}</p>}
            {bindSuccess && <p className="mt-3 text-[12px] text-emerald-dark">{bindSuccess}</p>}
          </AppSection>
        )}

        <AppSection className="!bg-white">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[#E8F4FD]">
                <IconTelegram size={18} className="text-[#229ED9]" />
              </div>
              <div>
                <div className="text-[14px] font-semibold text-ink">Telegram-бот</div>
                <div className="text-[12px] text-muted">
                  {user.telegram_connected
                    ? `@${user.telegram_username ?? "підключено"} · сповіщення увімкнено`
                    : "Нові авто прямо в месенджер"}
                </div>
              </div>
            </div>
            <div className="flex shrink-0 items-center gap-2">
              {user.telegram_connected ? (
                <>
                  <span className="flex items-center gap-1.5 text-[12px] font-medium text-emerald-dark">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald" />Підключено
                  </span>
                  <button onClick={disconnectTelegram} className="text-[12px] text-muted underline-offset-2 hover:text-red-500 hover:underline">
                    Відключити
                  </button>
                </>
              ) : (
                <Button variant="primary" size="sm" loading={tgLoading || polling} onClick={connectTelegram}>
                  {polling ? "Очікуємо..." : "Підключити"}
                </Button>
              )}
            </div>
          </div>
          {connectUrl && polling && (
            <p className="mt-4 rounded-xl bg-surface px-3 py-2 text-[12px] text-muted">
              Натисніть <strong>Start</strong> у боті — сторінка оновиться автоматично.
            </p>
          )}
          {!user.telegram_connected && (
            <p className="mt-3 text-[12px] text-muted">
              Або /start у{" "}
              {getTelegramBotUrl() ? (
                <a href={getTelegramBotUrl()} target="_blank" rel="noopener noreferrer" className="text-emerald-dark hover:underline">
                  {getTelegramBotMention()}
                </a>
              ) : (
                <span>бот (не налаштовано)</span>
              )}
            </p>
          )}
        </AppSection>

        <AppSection className="!bg-white">
          <Link href="/app/search" className="flex items-center gap-1 text-[13px] font-semibold text-emerald-dark hover:underline">
            Додати пошуковий запит <IconArrowRight size={11} />
          </Link>
        </AppSection>

        <AppSection className="!bg-white">
          <div className="text-[13px] font-semibold text-ink">Сесія</div>
          <Button variant="secondary" size="sm" className="mt-3" onClick={logout}>Вийти</Button>
        </AppSection>
      </div>
    </AppPage>
  );
}
