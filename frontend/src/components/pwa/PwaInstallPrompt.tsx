"use client";

import { useEffect, useState } from "react";
import { IconDownload, IconShare, IconX } from "@/components/icons";
import { PwaAppIcon } from "@/components/pwa/PwaAppIcon";
import { cn } from "@/lib/utils";

const DISMISS_KEY = "carbit_pwa_install_dismissed";
const DISMISS_DAYS = 14;

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

function isDismissedRecently() {
  const raw = localStorage.getItem(DISMISS_KEY);
  if (!raw) return false;
  const ts = Number(raw);
  if (Number.isNaN(ts)) return true;
  return Date.now() - ts < DISMISS_DAYS * 24 * 60 * 60 * 1000;
}

function isStandaloneMode() {
  return (
    window.matchMedia("(display-mode: standalone)").matches ||
    (window.navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

function isIOSDevice() {
  return /iPad|iPhone|iPod/.test(navigator.userAgent);
}

export function PwaInstallPrompt({ className }: { className?: string }) {
  const [visible, setVisible] = useState(false);
  const [ios, setIos] = useState(false);
  const [deferredPrompt, setDeferredPrompt] = useState<BeforeInstallPromptEvent | null>(null);

  useEffect(() => {
    if (isDismissedRecently() || isStandaloneMode()) return;

    const onIos = isIOSDevice();
    setIos(onIos);

    if (onIos) {
      setVisible(true);
      return;
    }

    const onBeforeInstall = (event: Event) => {
      event.preventDefault();
      setDeferredPrompt(event as BeforeInstallPromptEvent);
      setVisible(true);
    };

    window.addEventListener("beforeinstallprompt", onBeforeInstall);
    return () => window.removeEventListener("beforeinstallprompt", onBeforeInstall);
  }, []);

  const dismiss = () => {
    localStorage.setItem(DISMISS_KEY, String(Date.now()));
    setVisible(false);
  };

  const install = async () => {
    if (!deferredPrompt) return;
    await deferredPrompt.prompt();
    await deferredPrompt.userChoice;
    dismiss();
  };

  if (!visible) return null;

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl border border-emerald/20 bg-gradient-to-br from-emerald/10 via-white to-white p-4 sm:p-5",
        "shadow-[0_8px_32px_-8px_rgba(0,200,150,0.25)]",
        className,
      )}
    >
      <div className="absolute -right-6 -top-6 h-24 w-24 rounded-full bg-emerald/10 blur-2xl" />
      <button
        type="button"
        onClick={dismiss}
        className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-full text-muted transition-colors hover:bg-surface hover:text-ink"
        aria-label="Закрити"
      >
        <IconX size={14} />
      </button>

      <div className="flex items-start gap-4 pr-6">
        <div className="shrink-0 rounded-[18px] shadow-[0_8px_24px_-6px_rgba(0,0,0,0.35)] ring-1 ring-black/5">
          <PwaAppIcon size={56} />
        </div>

        <div className="min-w-0 flex-1">
          <div className="text-[11px] font-bold uppercase tracking-[0.14em] text-emerald-dark">
            Швидкий доступ
          </div>
          <h3 className="mt-1 text-[15px] font-bold tracking-tight text-ink sm:text-[16px]">
            Додай Carbit на головний екран
          </h3>
          <p className="mt-1 text-[12px] leading-relaxed text-muted sm:text-[13px]">
            {ios
              ? "Відкрий у Safari → «Поділитися» → «На екран Додому». Сповіщення та пошук — в один дотик."
              : "Встанови застосунок — миттєві сповіщення, швидкий доступ до пошуків без браузера."}
          </p>

          {ios ? (
            <div className="mt-3 inline-flex items-center gap-2 rounded-xl bg-ink px-3 py-2 text-[12px] font-semibold text-white">
              <IconShare size={14} />
              Поділитися → На екран «Додому»
            </div>
          ) : (
            <button
              type="button"
              onClick={install}
              disabled={!deferredPrompt}
              className="mt-3 inline-flex items-center gap-2 rounded-xl bg-emerald px-4 py-2.5 text-[12px] font-bold text-white transition-colors hover:bg-emerald-dark disabled:cursor-not-allowed disabled:opacity-60"
            >
              <IconDownload size={14} />
              Встановити Carbit
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
