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
  IconArrowRight,
  IconZap,
  IconLogOut,
  IconPlus,
  IconPlay,
} from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import { ApiError, telegram as telegramApi, billing as billingApi, users as usersApi } from "@/lib/api";
import { CodeInput } from "@/components/auth/CodeInput";
import { PLAN_LABELS, cn } from "@/lib/utils";
import {
  DISPLAY_CURRENCY_OPTIONS,
  resolveDisplayCurrency,
  type DisplayCurrency,
} from "@/lib/display-currency";
import { UserAvatar } from "@/components/ui/UserAvatar";
import { getTelegramBotMention, getTelegramBotUrl } from "@/lib/telegram";
import { requestOnboardingTour } from "@/lib/onboarding";
import {
  AppPage,
  AppSection,
  AppSectionGroup,
  AppSectionHeading,
  AppStatCard,
  AppStatGrid,
} from "@/components/layout/AppPage";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";
import { CancelRenewalDialog } from "@/components/billing/CancelRenewalDialog";
import { Alert } from "@/components/ui/Alert";
import { getPricingPlan, formatPlanPrice, planMonitorLimit } from "@/lib/plan-catalog";
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
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [polling, setPolling] = useState(false);
  const [bindEmail, setBindEmail] = useState("");
  const [bindCode, setBindCode] = useState("");
  const [bindStep, setBindStep] = useState<"idle" | "code">("idle");
  const [bindLoading, setBindLoading] = useState(false);
  const [bindError, setBindError] = useState("");
  const [bindSuccess, setBindSuccess] = useState("");
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

  return (
    <AppPage
      title="Акаунт"
      description="Профіль, підписка, сповіщення та налаштування кабінету"
    >
      <div className="space-y-7">
        <AppSectionGroup id="account-profile" label="Профіль">
          <AppSection className="!bg-white">
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
                      <label className="mb-1.5 block text-[11px] font-bold uppercase tracking-[0.1em] text-muted">
                        Імʼя
                      </label>
                      <input
                        type="text"
                        value={name}
                        onChange={e => setName(e.target.value)}
                        className="auth-input w-full"
                        autoFocus
                      />
                    </div>
                    <div>
                      <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted">
                        Валюта цін
                      </div>
                      <p className="mt-1 text-[12px] text-muted">
                        Для оголошень, фільтрів і Telegram
                      </p>
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
                      <div className="text-[16px] font-bold text-ink">{user.name}</div>
                      <div className="mt-0.5 text-[12px] text-muted">
                        {user.email_verified ? user.email : "Email не вказано"}
                      </div>
                      <div className="mt-1.5 text-[12px] text-muted">
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
          </AppSection>

          {!user.email_verified && (
            <AppSection className="!bg-white">
              <AppSectionHeading
                title="Email для входу"
                description="Додайте пошту для входу й відновлення доступу. Потрібне підтвердження кодом."
              />
              {bindStep === "idle" ? (
                <div className="space-y-3">
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
                <div className="space-y-3">
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
            </AppSection>
          )}
        </AppSectionGroup>

        {stats && (
          <AppSectionGroup id="account-overview" label="Огляд">
            <AppSection className="!bg-white" data-tour="tour-section-stats">
              <AppSectionHeading
                eyebrow="Статистика"
                title={`Тариф ${PLAN_LABELS[stats.plan] ?? stats.plan}`}
                description={`${stats.is_trial_active ? "Trial · " : ""}ліміт ${stats.searches_limit} моніторингів`}
                action={
                  <Link
                    href="/app/monitors"
                    className="text-[12px] font-semibold text-emerald-dark hover:underline"
                  >
                    Моніторинги →
                  </Link>
                }
              />
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
            </AppSection>
          </AppSectionGroup>
        )}

        <AppSectionGroup id="account-plan" label="Підписка та оплата">
          <AppSection className="!bg-white">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-[11px] font-bold uppercase tracking-[0.1em] text-muted">Тариф</div>
                <div className="mt-1 text-[20px] font-black text-ink">{planLabel}</div>
                {subscription?.is_trial_active && (
                  <div className="mt-1 text-[12px] text-emerald-dark">
                    Trial · обмежений безкоштовний доступ
                  </div>
                )}
                {user.plan !== "free" && subscription?.plan_expires_at && (
                  <div className="mt-1 text-[12px] text-muted">
                    Доступ до{" "}
                    {new Date(subscription.plan_expires_at).toLocaleDateString("uk-UA", {
                      day: "numeric",
                      month: "long",
                      year: "numeric",
                    })}
                    {subscription.recurring_active ? " · автопродовження увімкнено" : ""}
                  </div>
                )}
              </div>
              <Badge variant="emerald">
                <IconZap size={10} className="mr-1" />
                {user.plan === "free" ? "Free" : "Активний"}
              </Badge>
            </div>

            <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-3">
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
                  className="flex w-full items-center justify-center gap-2 rounded-2xl bg-emerald px-5 py-4 text-[16px] font-black text-white shadow-lg shadow-emerald/25 transition hover:bg-emerald-dark"
                >
                  <IconCreditCard size={18} />
                  Оформити підписку
                </Link>
                <div className="grid gap-2 sm:grid-cols-3">
                  {(
                    [
                      ["lite", "Старт", "10 пошуків"],
                      ["standard", "Про", "30 пошуків"],
                      ["pro", "Бізнес", "100 пошуків"],
                    ] as const
                  ).map(([id, name, slots]) => (
                    <Link
                      key={id}
                      href="/app/billing"
                      className="rounded-xl border border-border/70 bg-surface px-3 py-2.5 text-center transition hover:border-emerald/40"
                    >
                      <div className="text-[12px] font-bold text-ink">{name}</div>
                      <div className="mt-0.5 text-[13px] font-black text-emerald-dark">
                        {formatPlanPrice(id)}
                      </div>
                      <div className="text-[10px] text-muted">{slots}</div>
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
          </AppSection>

          {user.plan !== "free" && user.plan !== "pro" && (
            <SubscriptionPitch
              variant="banner"
              planId={user.plan}
              searchesLimit={user.searches_limit}
              searchesUsed={stats?.active_searches ?? 0}
              isTrial={Boolean(subscription?.is_trial_active)}
            />
          )}

          <AppSection className="!bg-white">
            <AppSectionHeading
              eyebrow="Оплата"
              title="Картка та платежі"
              description="Наступне списання, маска картки та історія через LiqPay"
            />
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl bg-surface px-3.5 py-3">
                <div className="text-[11px] text-muted">Наступний платіж</div>
                <div className="mt-1 text-[15px] font-semibold text-ink">
                  {subscription?.next_payment_at
                    ? new Date(subscription.next_payment_at).toLocaleDateString("uk-UA", {
                        day: "numeric",
                        month: "long",
                        year: "numeric",
                      })
                    : subscription?.plan_expires_at && user.plan !== "free"
                      ? `Доступ до ${new Date(subscription.plan_expires_at).toLocaleDateString("uk-UA")}`
                      : "—"}
                </div>
                {subscription?.recurring_active ? (
                  <div className="mt-0.5 text-[11px] text-emerald-dark">Автопродовження увімкнено</div>
                ) : user.plan !== "free" ? (
                  <div className="mt-0.5 text-[11px] text-muted">Без автопродовження</div>
                ) : null}
              </div>
              <div className="rounded-xl bg-surface px-3.5 py-3">
                <div className="text-[11px] text-muted">Картка</div>
                <div className="mt-1 text-[15px] font-semibold tracking-wide text-ink">
                  {subscription?.card_mask || "Не привʼязана"}
                </div>
                <div className="mt-0.5 text-[11px] text-muted">LiqPay · Visa / Mastercard</div>
              </div>
            </div>

            <div className="mt-5 text-[13px] font-semibold text-ink">Історія платежів</div>
            {(subscription?.payments?.length ?? 0) === 0 ? (
              <p className="mt-2 text-[13px] text-muted">
                Поки немає платежів. Після оплати тарифу записи зʼявляться тут.
              </p>
            ) : (
              <ul className="mt-3 divide-y divide-border/70 overflow-hidden rounded-xl border border-border/70">
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
              <Alert variant="success" className="mt-5" title="Готово">
                {cancelSuccess}
              </Alert>
            )}

            {user.plan !== "free" && subscription?.recurring_active && (
              <details className="mt-6 rounded-xl border border-dashed border-border/80 bg-surface/40 px-3.5 py-3">
                <summary className="cursor-pointer list-none text-[12px] text-muted marker:content-none [&::-webkit-details-marker]:hidden">
                  <span className="underline-offset-2 hover:text-ink hover:underline">
                    Керування автопродовженням
                  </span>
                </summary>
                <div className="mt-3 space-y-2 border-t border-border/60 pt-3">
                  <p className="text-[12px] leading-relaxed text-muted">
                    Можна зупинити щомісячні списання. Оплачений період лишиться активним до{" "}
                    {subscription.plan_expires_at
                      ? new Date(subscription.plan_expires_at).toLocaleDateString("uk-UA", {
                          day: "numeric",
                          month: "long",
                          year: "numeric",
                        })
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
          </AppSection>
        </AppSectionGroup>

        <AppSectionGroup id="account-telegram" label="Сповіщення">
          <AppSection className="!bg-white !p-5 sm:!p-6" data-tour="tour-section-telegram">
            <div className="flex flex-col gap-5 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-[#E8F4FD]">
                  <IconTelegram size={22} className="text-[#229ED9]" />
                </div>
                <div>
                  <div className="text-[16px] font-bold text-ink sm:text-[17px]">Telegram-бот</div>
                  <div className="mt-1 text-[14px] leading-snug text-muted">
                    {user.telegram_connected
                      ? `@${user.telegram_username ?? "підключено"} · сповіщення увімкнено`
                      : "Нові авто прямо в месенджер"}
                  </div>
                </div>
              </div>
              <div className="flex shrink-0 flex-wrap items-center gap-3">
                {user.telegram_connected ? (
                  <>
                    <span className="flex items-center gap-2 text-[14px] font-semibold text-emerald-dark">
                      <span className="h-2 w-2 rounded-full bg-emerald" />
                      Підключено
                    </span>
                    <Button variant="secondary" size="md" onClick={disconnectTelegram}>
                      Відключити
                    </Button>
                  </>
                ) : (
                  <Button
                    variant="primary"
                    size="md"
                    loading={tgLoading || polling}
                    onClick={connectTelegram}
                  >
                    {polling ? "Очікуємо..." : "Підключити"}
                  </Button>
                )}
              </div>
            </div>
            {connectUrl && polling && (
              <p className="mt-5 rounded-xl bg-surface px-4 py-3 text-[14px] text-muted">
                Натисніть <strong>Start</strong> у боті — сторінка оновиться автоматично.
              </p>
            )}
            {!user.telegram_connected && (
              <p className="mt-4 text-[14px] text-muted">
                Або /start у{" "}
                {getTelegramBotUrl() ? (
                  <a
                    href={getTelegramBotUrl()}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium text-emerald-dark hover:underline"
                  >
                    {getTelegramBotMention()}
                  </a>
                ) : (
                  <span>бот (не налаштовано)</span>
                )}
              </p>
            )}
          </AppSection>

          <AppSection className="!bg-white !p-5 sm:!p-6">
            <Link
              href="/app/dashboard"
              className="flex items-center justify-between gap-3 rounded-xl bg-surface/60 px-4 py-4 transition-colors hover:bg-surface"
            >
              <span className="flex items-center gap-3">
                <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-white shadow-sm">
                  <IconPlus size={20} className="text-emerald-dark" />
                </span>
                <span>
                  <span className="block text-[15px] font-semibold text-ink sm:text-[16px]">
                    Новий моніторинг
                  </span>
                  <span className="mt-0.5 block text-[12px] text-muted">
                    Налаштуйте фільтри на головній і збережіть запит
                  </span>
                </span>
              </span>
              <IconArrowRight size={18} className="shrink-0 text-muted" />
            </Link>
          </AppSection>
        </AppSectionGroup>

        <AppSectionGroup id="account-help" label="Допомога та сесія">
          <AppSection className="!bg-white">
            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <div className="text-[15px] font-bold text-ink">Інструкції кабінету</div>
                <p className="mt-1 text-[13px] text-muted">
                  Короткий тур по розділах — як при першому вході
                </p>
              </div>
              <Button
                type="button"
                variant="secondary"
                size="sm"
                className="w-fit gap-1.5 text-muted hover:text-ink"
                onClick={restartTour}
              >
                <IconPlay size={13} />
                Пройти інструкції ще раз
              </Button>
            </div>
          </AppSection>

          <AppSection className="!bg-white !p-5 sm:!p-6">
            <div className="text-[16px] font-bold text-ink">Сесія</div>
            <p className="mt-1.5 text-[14px] text-muted">Завершити поточний вхід у кабінет</p>
            <Button
              variant="danger"
              size="md"
              className="mt-4 gap-2 border-red-200 bg-red-50 px-5 py-2.5 text-[14px] font-semibold text-red-600 hover:border-red-300 hover:bg-red-100 hover:text-red-700"
              onClick={logout}
            >
              <IconLogOut size={16} />
              Вийти
            </Button>
          </AppSection>
        </AppSectionGroup>
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
    </AppPage>
  );
}