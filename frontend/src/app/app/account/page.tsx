"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  IconGear,
  IconCreditCard,
  IconTelegram,
  IconInstagram,
  IconZap,
  IconLogOut,
  IconPlay,
} from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError, telegram as telegramApi, billing as billingApi, users as usersApi } from "@/lib/api";
import { CodeInput } from "@/components/auth/CodeInput";
import { PhoneInput, normalizePhoneForApi } from "@/components/auth/PhoneInput";
import { PLAN_LABELS, cn } from "@/lib/utils";
import {
  DISPLAY_CURRENCY_OPTIONS,
  resolveDisplayCurrency,
  type DisplayCurrency,
} from "@/lib/display-currency";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { getTelegramBotMention, getTelegramBotUrl, getTelegramSupportBotMention, getTelegramSupportBotUrl } from "@/lib/telegram";
import { INSTAGRAM_HANDLE, INSTAGRAM_URL } from "@/lib/social-links";
import { requestOnboardingTour } from "@/lib/onboarding";
import {
  AppPage,
  AppSection,
  AppStatCard,
  AppStatGrid,
} from "@/components/layout/AppPage";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";
import { CancelRenewalDialog } from "@/components/billing/CancelRenewalDialog";
import { Alert } from "@/components/ui/Alert";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { getPricingPlan, formatPlanPrice, planMonitorLimit, planDeviceLimit } from "@/lib/plan-catalog";
import type { DashboardStats, Subscription } from "@/types/api";

export default function AccountPage() {
  const router = useRouter();
  const { user, updateProfile, logout, refreshUser } = useAuth();
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState("");
  const [currency, setCurrency] = useState<DisplayCurrency>("USD");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [connectUrl, setConnectUrl] = useState<string | null>(null);
  const [tgLoading, setTgLoading] = useState(false);
  const [tgError, setTgError] = useState("");
  const [disconnectOpen, setDisconnectOpen] = useState(false);
  const [disconnectLoading, setDisconnectLoading] = useState(false);
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [polling, setPolling] = useState(false);
  const [bindEmail, setBindEmail] = useState("");
  const [bindCode, setBindCode] = useState("");
  const [bindStep, setBindStep] = useState<"idle" | "code">("idle");
  const [bindLoading, setBindLoading] = useState(false);
  const [bindError, setBindError] = useState("");
  const [bindSuccess, setBindSuccess] = useState("");
  const [phoneBind, setPhoneBind] = useState("");
  const [phoneBindCode, setPhoneBindCode] = useState("");
  const [phoneBindStep, setPhoneBindStep] = useState<"idle" | "code">("idle");
  const [phoneBindLoading, setPhoneBindLoading] = useState(false);
  const [phoneBindError, setPhoneBindError] = useState("");
  const [phoneBindSuccess, setPhoneBindSuccess] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);
  const [cancelError, setCancelError] = useState("");
  const [cancelSuccess, setCancelSuccess] = useState("");

  useEffect(() => {
    billingApi.subscription().then(setSubscription).catch(() => {});
    usersApi.dashboard().then(setStats).catch(() => {});
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
  const displayCurrency = resolveDisplayCurrency(user.preferred_currency);
  const currencyOption = DISPLAY_CURRENCY_OPTIONS.find(o => o.value === displayCurrency);

  const startEdit = () => {
    setName(user.name);
    setCurrency(resolveDisplayCurrency(user.preferred_currency));
    setError("");
    setEditing(true);
  };

  const saveProfile = async () => {
    if (!name.trim()) {
      setError("Введіть ім'я");
      return;
    }
    setSaving(true);
    setError("");
    try {
      await updateProfile({
        name: name.trim(),
        preferred_currency: currency,
      });
      setEditing(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти");
    } finally {
      setSaving(false);
    }
  };

  const connectTelegram = async () => {
    setTgLoading(true);
    setTgError("");
    try {
      const link = await telegramApi.connectLink();
      setConnectUrl(link.bot_url);
      window.open(link.bot_url, "_blank");
      setPolling(true);
    } catch (err) {
      setTgError(err instanceof ApiError ? err.message : "Помилка");
    } finally {
      setTgLoading(false);
    }
  };

  const disconnectTelegram = async () => {
    setDisconnectLoading(true);
    try {
      await telegramApi.disconnect();
      await refreshUser();
      setConnectUrl(null);
      setDisconnectOpen(false);
    } finally {
      setDisconnectLoading(false);
    }
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

  const sendPhoneBindCode = async () => {
    setPhoneBindError("");
    setPhoneBindSuccess("");
    const normalized = normalizePhoneForApi(phoneBind);
    if (normalized.length < 12) {
      setPhoneBindError("Введіть повний номер телефону");
      return;
    }
    setPhoneBindLoading(true);
    try {
      await usersApi.sendPhoneBindCode(normalized);
      setPhoneBindStep("code");
      setPhoneBindSuccess("Код надіслано SMS");
    } catch (err) {
      setPhoneBindError(err instanceof ApiError ? err.message : "Не вдалося надіслати SMS");
    } finally {
      setPhoneBindLoading(false);
    }
  };

  const verifyPhoneBindCode = async () => {
    setPhoneBindError("");
    setPhoneBindSuccess("");
    if (phoneBindCode.length !== 6) {
      setPhoneBindError("Введіть 6-значний код");
      return;
    }
    setPhoneBindLoading(true);
    try {
      await usersApi.verifyPhoneBind(normalizePhoneForApi(phoneBind), phoneBindCode);
      await refreshUser();
      setPhoneBindStep("idle");
      setPhoneBindCode("");
      setPhoneBindSuccess("Телефон підтверджено");
    } catch (err) {
      setPhoneBindError(err instanceof ApiError ? err.message : "Невірний код");
    } finally {
      setPhoneBindLoading(false);
    }
  };

  const restartTour = () => {
    requestOnboardingTour();
    router.push("/app/dashboard");
  };

  const confirmCancelRenewal = async (payload: { reason: string; note: string }) => {
    setCancelLoading(true);
    setCancelError("");
    try {
      const sub = await billingApi.unsubscribe({
        reason: payload.reason,
        note: payload.note || undefined,
      });
      setSubscription(sub);
      await refreshUser();
      setCancelOpen(false);
      setCancelSuccess(
        "Автопродовження скасовано. Доступ збережеться до кінця оплаченого періоду.",
      );
    } catch (err) {
      setCancelError(
        err instanceof ApiError ? err.message : "Не вдалося скасувати автопродовження",
      );
    } finally {
      setCancelLoading(false);
    }
  };

  const formatDate = (iso: string) =>
    new Date(iso).toLocaleDateString("uk-UA", {
      day: "numeric",
      month: "long",
      year: "numeric",
    });

  return (
    <AppPage title="Акаунт">
      <div className="space-y-4 sm:space-y-5">
        {/* Профіль */}
        <AppSection id="account-profile" className="!bg-white">
          <div className="flex items-start gap-4">
            <UserAvatar
              name={user.name}
              avatarUrl={user.avatar_url}
              className="h-14 w-14 shrink-0 text-[18px] font-black"
            />
            <div className="min-w-0 flex-1">
              {editing ? (
                <div className="space-y-4">
                  <div>
                    <label className="mb-1.5 block text-[13px] font-medium text-muted">Імʼя</label>
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      className="auth-input w-full"
                      autoFocus
                    />
                  </div>
                  <div>
                    <div className="text-[13px] font-medium text-muted">Валюта цін</div>
                    <p className="mt-0.5 text-[12px] text-muted">Для оголошень, фільтрів і Telegram</p>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      {DISPLAY_CURRENCY_OPTIONS.map(option => {
                        const active = currency === option.value;
                        return (
                          <button
                            key={option.value}
                            type="button"
                            disabled={saving}
                            onClick={() => setCurrency(option.value)}
                            className={cn(
                              "rounded-xl border px-3.5 py-2 text-left transition-colors",
                              active
                                ? "border-emerald bg-emerald-light/40 text-ink"
                                : "border-border/80 bg-white text-muted hover:border-emerald/30 hover:text-ink",
                            )}
                          >
                            <div className="text-[13px] font-bold">{option.label}</div>
                            <div className="text-[11px] opacity-70">{option.suffix}</div>
                          </button>
                        );
                      })}
                    </div>
                  </div>
                  {error && <p className="text-[12px] text-red-600">{error}</p>}
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm" loading={saving} onClick={saveProfile}>
                      Зберегти
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setEditing(false)}
                      disabled={saving}
                    >
                      Скасувати
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between sm:gap-4">
                  <div className="min-w-0">
                    <div className="text-[17px] font-bold text-ink">{user.name}</div>
                    <div className="mt-0.5 text-[13px] text-muted">
                      {user.email_verified ? user.email : "Email не вказано"}
                    </div>
                    <div className="mt-1 text-[13px] text-muted">
                      Телефон:{" "}
                      <span className="font-semibold text-ink">
                        {user.phone_verified && user.phone ? user.phone : "не підтверджено"}
                      </span>
                    </div>
                    <div className="mt-1.5 text-[13px] text-muted">
                      Валюта:{" "}
                      <span className="font-semibold text-ink">
                        {currencyOption?.label ?? displayCurrency}
                        {currencyOption ? ` (${currencyOption.suffix})` : ""}
                      </span>
                    </div>
                  </div>
                  <Button variant="secondary" size="sm" className="w-fit shrink-0 gap-1.5" onClick={startEdit}>
                    <IconGear size={13} /> Редагувати
                  </Button>
                </div>
              )}
            </div>
          </div>

          {!user.email_verified && (
            <div className="mt-5 border-t border-border/60 pt-5">
              <p className="text-[13px] font-semibold text-ink">Додати email для входу</p>
              <p className="mt-1 text-[12px] text-muted">
                Потрібне підтвердження кодом — для входу й відновлення доступу.
              </p>
              {bindStep === "idle" ? (
                <div className="mt-3 space-y-3">
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
                <div className="mt-3 space-y-3">
                  <p className="text-[12px] text-muted">
                    Код надіслано на <strong>{bindEmail}</strong>
                  </p>
                  <CodeInput value={bindCode} onChange={setBindCode} />
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm" loading={bindLoading} onClick={verifyBindCode}>
                      Підтвердити
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={bindLoading}
                      onClick={() => {
                        setBindStep("idle");
                        setBindCode("");
                        setBindError("");
                      }}
                    >
                      Змінити email
                    </Button>
                  </div>
                </div>
              )}
              {bindError && <p className="mt-3 text-[12px] text-red-600">{bindError}</p>}
              {bindSuccess && <p className="mt-3 text-[12px] text-emerald-dark">{bindSuccess}</p>}
            </div>
          )}

          {!user.phone_verified && (
            <div className="mt-5 border-t border-border/60 pt-5">
              <p className="text-[13px] font-semibold text-ink">Підтвердити номер телефону</p>
              <p className="mt-1 text-[12px] text-muted">
                SMS-код через TurboSMS — для входу по телефону та безпеки акаунта.
              </p>
              {phoneBindStep === "idle" ? (
                <div className="mt-3 space-y-3">
                  <PhoneInput value={phoneBind} onChange={setPhoneBind} disabled={phoneBindLoading} />
                  <Button variant="primary" size="sm" loading={phoneBindLoading} onClick={sendPhoneBindCode}>
                    Надіслати код SMS
                  </Button>
                </div>
              ) : (
                <div className="mt-3 space-y-3">
                  <p className="text-[12px] text-muted">
                    Код надіслано на <strong>+380 {phoneBind}</strong>
                  </p>
                  <CodeInput value={phoneBindCode} onChange={setPhoneBindCode} />
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm" loading={phoneBindLoading} onClick={verifyPhoneBindCode}>
                      Підтвердити
                    </Button>
                    <Button
                      variant="secondary"
                      size="sm"
                      disabled={phoneBindLoading}
                      onClick={() => {
                        setPhoneBindStep("idle");
                        setPhoneBindCode("");
                        setPhoneBindError("");
                      }}
                    >
                      Змінити номер
                    </Button>
                  </div>
                </div>
              )}
              {phoneBindError && <p className="mt-3 text-[12px] text-red-600">{phoneBindError}</p>}
              {phoneBindSuccess && <p className="mt-3 text-[12px] text-emerald-dark">{phoneBindSuccess}</p>}
            </div>
          )}
        </AppSection>

        {/* Підписка + статистика + оплата */}
        <AppSection id="account-plan" className="!bg-white">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-[17px] font-bold text-ink">{planLabel}</div>
              {subscription?.is_trial_active && (
                <div className="mt-1 text-[13px] text-emerald-dark">Пробний період</div>
              )}
              {user.plan !== "free" && subscription?.plan_expires_at && (
                <div className="mt-1 text-[13px] text-muted">
                  Доступ до {formatDate(subscription.plan_expires_at)}
                  {subscription.recurring_active ? " · автопродовження" : ""}
                </div>
              )}
            </div>
            <Badge variant="emerald">
              <IconZap size={10} className="mr-1" />
              {user.plan === "free" ? "Free" : "Активний"}
            </Badge>
          </div>

          {stats && (
            <div className="mt-5" data-tour="tour-section-stats">
              <AppStatGrid>
                <AppStatCard
                  label="Активних"
                  value={stats.active_searches}
                  sub={`з ${stats.searches_limit}`}
                />
                <AppStatCard
                  label="Нових сьогодні"
                  value={stats.new_listings_today}
                  sub={`${stats.new_listings_yesterday} вчора`}
                  accent={stats.new_listings_today > 0}
                />
                <AppStatCard label="В обраному" value={stats.favorites_count} sub="авто" />
                <AppStatCard
                  label="Непрочитаних"
                  value={stats.unread_notifications}
                  sub="сповіщень"
                  accent={stats.unread_notifications > 0}
                />
              </AppStatGrid>
            </div>
          )}

          <div className="mt-5 grid grid-cols-2 gap-2 sm:grid-cols-4 sm:gap-3">
            {[
              [String(user.searches_limit), "моніторингів"],
              [String(planDeviceLimit(user.plan)), "пристроїв"],
              ["3", "джерела"],
              [user.telegram_connected ? "✓" : "—", "Telegram"],
            ].map(([v, l]) => (
              <div key={l} className="rounded-xl bg-surface px-2.5 py-3 text-center sm:px-3">
                <div className="text-[16px] font-black text-ink sm:text-[18px]">{v}</div>
                <div className="mt-0.5 text-[11px] text-muted">{l}</div>
              </div>
            ))}
          </div>

          {(() => {
            const meta = getPricingPlan(user.plan);
            const features = meta?.features?.slice(0, 4) ?? [];
            if (features.length === 0) return null;
            return (
              <ul className="mt-4 space-y-1.5">
                {features.map(f => (
                  <li key={f} className="flex gap-2 text-[12px] text-muted">
                    <span className="mt-0.5 text-emerald-dark">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
            );
          })()}

          {user.plan === "free" ? (
            <div className="mt-5 space-y-3">
              <Link
                href="/app/billing"
                className="flex w-full items-center justify-center gap-2 rounded-2xl bg-emerald px-5 py-3.5 text-[15px] font-bold text-white shadow-lg shadow-emerald/25 transition hover:bg-emerald-dark"
              >
                <IconCreditCard size={18} />
                Оформити підписку
              </Link>
              <div className="grid gap-2 sm:grid-cols-3">
                {(
                  [
                    ["lite", "Старт"],
                    ["standard", "Про"],
                    ["pro", "Бізнес"],
                  ] as const
                ).map(([id, name]) => (
                  <Link
                    key={id}
                    href="/app/billing"
                    className="rounded-xl border border-border/70 bg-surface px-3 py-2.5 text-center transition hover:border-emerald/40"
                  >
                    <div className="text-[12px] font-bold text-ink">{name}</div>
                    <div className="mt-0.5 text-[13px] font-black text-emerald-dark">
                      {formatPlanPrice(id)}
                    </div>
                  </Link>
                ))}
              </div>
            </div>
          ) : (
            <div className="mt-5 space-y-3">
              <div className="flex flex-wrap gap-3">
                <Link href="/app/billing">
                  <Button variant="emerald" size="md" className="gap-1.5">
                    <IconCreditCard size={13} /> Змінити тариф
                  </Button>
                </Link>
                <Link href="/pricing">
                  <Button variant="secondary" size="md">
                    Порівняти тарифи
                  </Button>
                </Link>
              </div>
              {user.plan !== "pro" && (
                <Alert
                  variant="info"
                  title={`Потрібно більше ніж ${user.searches_limit}?`}
                  action={
                    <Link
                      href="/app/billing"
                      className="inline-flex items-center justify-center rounded-full bg-sky-600 px-4 py-2 text-[12px] font-bold text-white hover:bg-sky-700"
                    >
                      Змінити тариф
                    </Link>
                  }
                >
                  Наступний рівень — до{" "}
                  {planMonitorLimit(user.plan === "lite" ? "standard" : "pro")} моніторингів. При
                  апгрейді залишок поточного періоду зараховується в доплату.
                </Alert>
              )}
            </div>
          )}

          {user.plan !== "free" && user.plan !== "pro" && (
            <div className="mt-4">
              <SubscriptionPitch
                variant="banner"
                planId={user.plan}
                searchesLimit={user.searches_limit}
                searchesUsed={stats?.active_searches ?? 0}
                isTrial={Boolean(subscription?.is_trial_active)}
              />
            </div>
          )}

          <div className="mt-6 border-t border-border/60 pt-5">
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-surface px-3.5 py-3">
                <div className="text-[12px] text-muted">Наступний платіж</div>
                <div className="mt-1 text-[14px] font-semibold text-ink">
                  {subscription?.next_payment_at
                    ? formatDate(subscription.next_payment_at)
                    : subscription?.plan_expires_at && user.plan !== "free"
                      ? `Доступ до ${formatDate(subscription.plan_expires_at)}`
                      : "—"}
                </div>
                {subscription?.recurring_active ? (
                  <div className="mt-0.5 text-[11px] text-emerald-dark">Автопродовження увімкнено</div>
                ) : user.plan !== "free" ? (
                  <div className="mt-0.5 text-[11px] text-muted">Без автопродовження</div>
                ) : null}
              </div>
              <div className="rounded-xl bg-surface px-3.5 py-3">
                <div className="text-[12px] text-muted">Картка</div>
                <div className="mt-1 text-[14px] font-semibold tracking-wide text-ink">
                  {subscription?.card_mask || "Не привʼязана"}
                </div>
                <div className="mt-0.5 text-[11px] text-muted">LiqPay · Visa / Mastercard</div>
              </div>
            </div>

            {(subscription?.payments?.length ?? 0) > 0 && (
              <ul className="mt-4 divide-y divide-border/70 overflow-hidden rounded-xl border border-border/70">
                {(subscription?.payments ?? []).map(payment => {
                  const ok = payment.status === "success";
                  return (
                    <li
                      key={payment.id}
                      className="flex flex-wrap items-center justify-between gap-2 bg-white px-3.5 py-3"
                    >
                      <div className="min-w-0">
                        <div className="truncate text-[13px] font-semibold text-ink">
                          {payment.plan_name}
                          {payment.card_mask ? (
                            <span className="ml-2 font-medium text-muted">{payment.card_mask}</span>
                          ) : null}
                        </div>
                        <div className="mt-0.5 text-[11px] text-muted">
                          {new Date(payment.paid_at).toLocaleString("uk-UA", {
                            day: "numeric",
                            month: "short",
                            year: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-[14px] font-bold text-ink">
                          {payment.amount.toLocaleString("uk-UA")} {payment.currency}
                        </div>
                        <div
                          className={cn(
                            "text-[11px] font-medium",
                            ok ? "text-emerald-dark" : "text-red-600",
                          )}
                        >
                          {ok ? "Успішно" : "Невдало"}
                        </div>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}

            {cancelSuccess && (
              <Alert variant="success" className="mt-4" title="Готово">
                {cancelSuccess}
              </Alert>
            )}

            {user.plan !== "free" && subscription?.recurring_active && (
              <details className="mt-4 rounded-xl border border-dashed border-border/80 bg-surface/40 px-3.5 py-3">
                <summary className="cursor-pointer list-none text-[12px] text-muted marker:content-none [&::-webkit-details-marker]:hidden">
                  <span className="underline-offset-2 hover:text-ink hover:underline">
                    Керування автопродовженням
                  </span>
                </summary>
                <div className="mt-3 space-y-2 border-t border-border/60 pt-3">
                  <p className="text-[12px] leading-relaxed text-muted">
                    Можна зупинити щомісячні списання. Оплачений період лишиться активним до{" "}
                    {subscription.plan_expires_at
                      ? formatDate(subscription.plan_expires_at)
                      : "його завершення"}
                    .
                  </p>
                  <button
                    type="button"
                    onClick={() => {
                      setCancelError("");
                      setCancelOpen(true);
                    }}
                    className="text-[12px] font-medium text-muted underline-offset-2 transition hover:text-red-600 hover:underline"
                  >
                    Скасувати автопродовження…
                  </button>
                </div>
              </details>
            )}
          </div>
        </AppSection>

        {/* Telegram + підтримка + допомога + вихід */}
        <AppSection id="account-more" className="!bg-white !p-0 overflow-hidden" data-tour="tour-section-telegram">
          <div className="divide-y divide-border/60">
            <div className="flex flex-col gap-3 px-4 py-4 sm:flex-row sm:items-center sm:justify-between sm:px-5">
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#E8F4FD]">
                  <IconTelegram size={18} className="text-[#229ED9]" />
                </span>
                <div className="min-w-0">
                  <div className="text-[14px] font-semibold text-ink">Telegram-сповіщення</div>
                  <div className="mt-0.5 text-[12px] text-muted">
                    {user.telegram_connected
                      ? `@${user.telegram_username ?? "підключено"}`
                      : getTelegramBotUrl()
                        ? `Бот ${getTelegramBotMention()}`
                        : "Нові авто в месенджер"}
                  </div>
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-2">
                {user.telegram_connected ? (
                  <>
                    <span className="flex items-center gap-1.5 text-[12px] font-semibold text-emerald-dark">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald" />
                      Підключено
                    </span>
                    <Button variant="secondary" size="sm" onClick={() => setDisconnectOpen(true)}>
                      Відключити
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="primary"
                    size="sm"
                    loading={tgLoading || polling}
                    onClick={() => void connectTelegram()}
                  >
                    {polling ? "Очікуємо…" : "Підключити"}
                  </Button>
                )}
              </div>
            </div>
            {connectUrl && polling && (
              <p className="bg-surface/50 px-4 py-3 text-[12px] text-muted sm:px-5">
                Натисніть <strong>Start</strong> у боті — сторінка оновиться автоматично.
              </p>
            )}

            <a
              href={INSTAGRAM_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between gap-3 px-4 py-4 transition-colors hover:bg-surface/50 sm:px-5"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-tr from-[#f58529]/15 via-[#dd2a7b]/15 to-[#8134af]/15">
                  <IconInstagram size={18} className="text-[#dd2a7b]" />
                </span>
                <div className="min-w-0">
                  <div className="text-[14px] font-semibold text-ink">Instagram</div>
                  <div className="mt-0.5 text-[12px] text-muted">
                    @{INSTAGRAM_HANDLE} · новини, фото авто, оновлення
                  </div>
                </div>
              </div>
              <span className="shrink-0 text-[12px] font-semibold text-[#dd2a7b]">Підписатися</span>
            </a>

            <a
              href={getTelegramSupportBotUrl()}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-between gap-3 px-4 py-4 transition-colors hover:bg-surface/50 sm:px-5"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#E8F4FD]">
                  <IconTelegram size={18} className="text-[#229ED9]" />
                </span>
                <div className="min-w-0">
                  <div className="text-[14px] font-semibold text-ink">Підтримка</div>
                  <div className="mt-0.5 text-[12px] text-muted">
                    {getTelegramSupportBotMention()} · тариф, оплата, сервіс
                  </div>
                </div>
              </div>
              <span className="shrink-0 text-[12px] font-semibold text-[#229ED9]">Написати</span>
            </a>

            <button
              type="button"
              onClick={restartTour}
              className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-surface/50 sm:px-5"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-surface">
                  <IconPlay size={16} className="text-ink/70" />
                </span>
                <div className="min-w-0">
                  <div className="text-[14px] font-semibold text-ink">Інструкції кабінету</div>
                  <div className="mt-0.5 text-[12px] text-muted">Короткий тур по розділах</div>
                </div>
              </div>
              <span className="shrink-0 text-[12px] font-medium text-muted">Пройти</span>
            </button>

            <button
              type="button"
              onClick={logout}
              className="flex w-full items-center justify-between gap-3 px-4 py-4 text-left transition-colors hover:bg-red-50/80 sm:px-5"
            >
              <div className="flex min-w-0 items-center gap-3">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-red-50">
                  <IconLogOut size={16} className="text-red-600" />
                </span>
                <div className="min-w-0">
                  <div className="text-[14px] font-semibold text-red-600">Вийти</div>
                  <div className="mt-0.5 text-[12px] text-muted">Завершити сесію в кабінеті</div>
                </div>
              </div>
            </button>
          </div>
        </AppSection>
      </div>

      <CancelRenewalDialog
        open={cancelOpen}
        expiresAt={subscription?.plan_expires_at}
        loading={cancelLoading}
        error={cancelError}
        onClose={() => {
          if (!cancelLoading) setCancelOpen(false);
        }}
        onConfirm={payload => void confirmCancelRenewal(payload)}
      />

      <ConfirmDialog
        open={disconnectOpen}
        title="Відключити Telegram-бот?"
        description="Сповіщення про нові авто перестануть надходити в Telegram. Підключити знову можна будь-коли."
        confirmLabel="Відключити"
        cancelLabel="Скасувати"
        variant="danger"
        loading={disconnectLoading}
        onClose={() => {
          if (!disconnectLoading) setDisconnectOpen(false);
        }}
        onConfirm={() => void disconnectTelegram()}
      />

      <ConfirmDialog
        open={Boolean(tgError)}
        title="Не вдалося підключити Telegram"
        description={tgError}
        alertOnly
        confirmLabel="Зрозуміло"
        variant="primary"
        onClose={() => setTgError("")}
      />
    </AppPage>
  );
}
