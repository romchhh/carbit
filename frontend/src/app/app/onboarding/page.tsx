"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { LogoIcon } from "@/components/brand/LogoIcon";
import { IconSearch, IconBell, IconZap } from "@/components/icons";
import { cn } from "@/lib/utils";
import { useAuth } from "@/contexts/AuthProvider";
import { completeOnboarding as completeOnboardingLocal } from "@/lib/onboarding";
import { users as usersApi } from "@/lib/api";

const steps = [
  {
    icon: IconZap,
    title: "Ласкаво просимо!",
    desc: "Carbit моніторить AUTO.RIA, OLX і Telegram 24/7 — ви отримуєте нові авто раніше за конкурентів.",
    accent: "emerald",
  },
  {
    icon: IconSearch,
    title: "Створіть пошуковий запит",
    desc: "Оберіть марку, модель, бюджет і регіон. Ми знайдемо відповідні оголошення автоматично.",
    accent: "ink",
  },
  {
    icon: IconBell,
    title: "Отримуйте сповіщення",
    desc: "Нові авто з'являються в кабінеті за лічені хвилини. Підключіть Telegram — і не пропустите жодного лота.",
    accent: "emerald",
  },
];

export default function OnboardingPage() {
  const { user } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(0);

  if (!user) return null;

  const current = steps[step];
  const Icon = current.icon;
  const isLast = step === steps.length - 1;
  const firstName = user.name.split(" ")[0];

  const finish = async () => {
    try { await usersApi.completeOnboarding(); } catch { /* ignore */ }
    completeOnboardingLocal();
    router.push("/app/search");
  };

  const next = () => {
    if (isLast) finish();
    else setStep(s => s + 1);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-ink flex items-center justify-center p-4 sm:p-6">
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-emerald/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-1/4 right-1/4 w-64 h-64 bg-emerald/5 rounded-full blur-[80px]" />
      </div>

      <div className="relative w-full max-w-[480px]">
        <div className="flex items-center justify-center gap-2.5 mb-8">
          <span className="w-10 h-10 rounded-full bg-white/10 ring-1 ring-white/20 flex items-center justify-center">
            <LogoIcon size={22} light />
          </span>
          <span className="text-white text-[17px] font-bold tracking-tight">Carbit</span>
        </div>

        <div className="bg-white rounded-[1.75rem] p-8 sm:p-10 shadow-2xl shadow-black/40">
          <div className="flex justify-center gap-2 mb-8">
            {steps.map((_, i) => (
              <div
                key={i}
                className={cn(
                  "h-1.5 rounded-full transition-all duration-500",
                  i === step ? "w-8 bg-emerald" : i < step ? "w-4 bg-emerald/50" : "w-4 bg-border",
                )}
              />
            ))}
          </div>

          <div className="text-center mb-8">
            <div className={cn(
              "w-16 h-16 rounded-2xl mx-auto mb-5 flex items-center justify-center",
              current.accent === "emerald" ? "bg-emerald-light text-emerald-dark" : "bg-surface text-ink",
            )}>
              <Icon size={28} />
            </div>

            {step === 0 && (
              <p className="text-[13px] text-emerald-dark font-semibold mb-2">
                Привіт, {firstName}! 👋
              </p>
            )}

            <h1 className="text-[26px] font-black tracking-[-0.02em] text-ink leading-tight mb-3">
              {current.title}
            </h1>
            <p className="text-[14px] text-muted leading-relaxed max-w-[340px] mx-auto">
              {current.desc}
            </p>
          </div>

          <div className="space-y-3">
            <Button
              onClick={next}
              variant="emerald"
              size="md"
              showArrow
              className="w-full"
            >
              {isLast ? "Створити перший запит" : "Далі"}
            </Button>

            {!isLast && (
              <button
                type="button"
                onClick={finish}
                className="w-full py-2.5 text-[13px] text-muted hover:text-ink transition-colors"
              >
                Пропустити
              </button>
            )}
          </div>
        </div>

        <p className="mt-6 text-center text-[12px] text-white/30">
          Крок {step + 1} з {steps.length}
        </p>
      </div>
    </div>
  );
}
