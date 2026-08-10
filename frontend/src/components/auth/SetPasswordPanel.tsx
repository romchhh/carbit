"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { ApiError } from "@/lib/api";
import { cn } from "@/lib/utils";

type Props = {
  hasPassword: boolean;
  onSave: (password: string, currentPassword?: string) => Promise<void>;
  defaultOpen?: boolean;
  hint?: string;
};

export function SetPasswordPanel({ hasPassword, onSave, defaultOpen = false, hint }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [currentPassword, setCurrentPassword] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const actionLabel = hasPassword ? "Змінити пароль" : "Встановити пароль";

  const resetFields = () => {
    setCurrentPassword("");
    setPassword("");
    setConfirm("");
  };

  const handleClose = () => {
    setOpen(false);
    resetFields();
    setError("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (password.length < 8) {
      setError("Пароль — мінімум 8 символів");
      return;
    }
    if (password !== confirm) {
      setError("Паролі не збігаються");
      return;
    }

    setLoading(true);
    try {
      await onSave(password, hasPassword ? currentPassword : undefined);
      setSuccess(hasPassword ? "Пароль оновлено" : "Пароль збережено — команда може входити без SMS");
      resetFields();
      setOpen(false);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Не вдалося зберегти пароль");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <p className="text-[13px] font-semibold text-ink">Пароль для входу</p>
      {!open ? (
        <div className="mt-3">
          <Button type="button" variant="secondary" size="sm" onClick={() => setOpen(true)}>
            {actionLabel}
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} className="mt-3 space-y-3 rounded-xl border border-border/70 bg-surface/40 p-3.5 sm:p-4">
          <div className="flex items-start justify-between gap-3">
            <p className="text-[12px] leading-relaxed text-muted">
              {hint ??
                (hasPassword
                  ? "Змініть пароль для входу за номером телефону."
                  : "Встановіть пароль — колеги зможуть входити за номером і паролем без SMS-коду кожного разу.")}
            </p>
            <button
              type="button"
              onClick={handleClose}
              className="shrink-0 text-[12px] font-medium text-muted transition-colors hover:text-ink"
            >
              Скасувати
            </button>
          </div>
          {hasPassword && (
            <input
              type="password"
              className="auth-input w-full"
              placeholder="Поточний пароль"
              value={currentPassword}
              onChange={e => setCurrentPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          )}
          <input
            type="password"
            className="auth-input w-full"
            placeholder={hasPassword ? "Новий пароль" : "Пароль (мін. 8 символів)"}
            value={password}
            onChange={e => setPassword(e.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
          />
          <input
            type="password"
            className="auth-input w-full"
            placeholder="Повторіть пароль"
            value={confirm}
            onChange={e => setConfirm(e.target.value)}
            autoComplete="new-password"
            required
            minLength={8}
          />
          {error && <p className="text-[12px] text-red-600">{error}</p>}
          {success && <p className={cn("text-[12px] text-emerald-dark")}>{success}</p>}
          <Button type="submit" variant="primary" size="sm" loading={loading}>
            {actionLabel}
          </Button>
        </form>
      )}
      {!open && success && <p className="mt-2 text-[12px] text-emerald-dark">{success}</p>}
    </div>
  );
}
