"use client";

import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import { createPortal } from "react-dom";
import { Button } from "@/components/ui/Button";
import { cn } from "@/lib/utils";
import {
  ONBOARDING_TOUR_STEPS,
  type OnboardingTourStep,
  type TourPlacement,
} from "@/lib/onboarding-tour-steps";

const SPOTLIGHT_PADDING = 10;
const TOOLTIP_GAP = 14;
const DEFAULT_PATH = "/app/dashboard";

type Rect = {
  top: number;
  left: number;
  width: number;
  height: number;
};

function findVisibleTourTarget(targetId: string): HTMLElement | null {
  const nodes = document.querySelectorAll<HTMLElement>(`[data-tour="${targetId}"]`);
  for (const node of nodes) {
    const rect = node.getBoundingClientRect();
    if (rect.width <= 0 || rect.height <= 0) continue;
    const style = window.getComputedStyle(node);
    if (style.display === "none" || style.visibility === "hidden") continue;
    return node;
  }
  return nodes[0] ?? null;
}

function measureTarget(targetId?: string): Rect | null {
  if (!targetId) return null;
  const el = findVisibleTourTarget(targetId);
  if (!el) return null;
  const rect = el.getBoundingClientRect();
  return {
    top: rect.top - SPOTLIGHT_PADDING,
    left: rect.left - SPOTLIGHT_PADDING,
    width: rect.width + SPOTLIGHT_PADDING * 2,
    height: rect.height + SPOTLIGHT_PADDING * 2,
  };
}

function tooltipPosition(
  target: Rect | null,
  placement: TourPlacement,
  tooltipSize: { width: number; height: number },
): { top: number; left: number } {
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  const margin = 12;
  const w = tooltipSize.width;
  const h = tooltipSize.height;

  if (!target || placement === "center") {
    return {
      top: Math.max(margin, (vh - h) / 2),
      left: Math.max(margin, (vw - w) / 2),
    };
  }

  let top = target.top + target.height + TOOLTIP_GAP;
  let left = target.left + target.width / 2 - w / 2;

  if (placement === "top") {
    top = target.top - h - TOOLTIP_GAP;
  } else if (placement === "left") {
    top = target.top + target.height / 2 - h / 2;
    left = target.left - w - TOOLTIP_GAP;
  } else if (placement === "right") {
    top = target.top + target.height / 2 - h / 2;
    left = target.left + target.width + TOOLTIP_GAP;
  }

  top = Math.min(Math.max(margin, top), vh - h - margin);
  left = Math.min(Math.max(margin, left), vw - w - margin);
  return { top, left };
}

async function waitForTarget(targetId: string, timeoutMs = 3500): Promise<boolean> {
  const started = Date.now();
  return new Promise(resolve => {
    const tick = () => {
      if (findVisibleTourTarget(targetId)) {
        resolve(true);
        return;
      }
      if (Date.now() - started >= timeoutMs) {
        resolve(false);
        return;
      }
      requestAnimationFrame(tick);
    };
    tick();
  });
}

type Props = {
  firstName?: string;
  onComplete: () => void;
  onSkip?: () => void;
};

export function OnboardingTour({ firstName, onComplete, onSkip }: Props) {
  const router = useRouter();
  const pathname = usePathname();
  const [stepIndex, setStepIndex] = useState(0);
  const [targetRect, setTargetRect] = useState<Rect | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ top: 0, left: 0 });
  const [mounted, setMounted] = useState(false);
  const [stepReady, setStepReady] = useState(false);

  const steps = ONBOARDING_TOUR_STEPS;
  const step: OnboardingTourStep = steps[stepIndex];
  const stepPath = step.path ?? DEFAULT_PATH;
  const isFirst = stepIndex === 0;
  const isLast = stepIndex === steps.length - 1;
  const placement = step.placement ?? (step.target ? "bottom" : "center");

  const refreshGeometry = useCallback(() => {
    const targetId = step.target;
    if (targetId) {
      const el = findVisibleTourTarget(targetId);
      el?.scrollIntoView({ behavior: "smooth", block: "center", inline: "nearest" });
    }

    window.requestAnimationFrame(() => {
      const rect = measureTarget(targetId);
      setTargetRect(rect);

      const tooltipEl = document.getElementById("onboarding-tour-tooltip");
      const size = tooltipEl
        ? { width: tooltipEl.offsetWidth, height: tooltipEl.offsetHeight }
        : { width: 340, height: 260 };
      setTooltipPos(tooltipPosition(rect, placement, size));
    });
  }, [step.target, placement]);

  useEffect(() => setMounted(true), []);

  useEffect(() => {
    if (pathname === stepPath) return;
    router.push(stepPath);
  }, [pathname, router, stepPath]);

  useEffect(() => {
    let cancelled = false;
    setStepReady(false);
    setTargetRect(null);

    if (pathname !== stepPath) return;

    const prepare = async () => {
      await new Promise(r => setTimeout(r, 280));
      if (cancelled) return;

      if (step.target) {
        await waitForTarget(step.target);
      }
      if (cancelled) return;
      setStepReady(true);
    };

    void prepare();
    return () => {
      cancelled = true;
    };
  }, [pathname, stepPath, step.target, stepIndex]);

  useLayoutEffect(() => {
    if (!stepReady) return;
    refreshGeometry();
    const onResize = () => refreshGeometry();
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
    };
  }, [refreshGeometry, stepReady, stepIndex]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  const goNext = () => {
    if (isLast) onComplete();
    else setStepIndex(i => i + 1);
  };

  const goBack = () => setStepIndex(i => Math.max(0, i - 1));

  const handleSkip = () => {
    if (onSkip) onSkip();
    else onComplete();
  };

  if (!mounted) return null;

  const title =
    step.id === "welcome" && firstName
      ? `${step.title.replace("!", "")}, ${firstName}!`
      : step.title;

  return createPortal(
    <div className="fixed inset-0 z-[250]" role="dialog" aria-modal="true" aria-labelledby="onboarding-tour-title">
      <div className="absolute inset-0 bg-ink/55 backdrop-blur-[1px]" aria-hidden />

      {stepReady && targetRect && (
        <div
          className="pointer-events-none absolute rounded-2xl ring-2 ring-emerald ring-offset-2 ring-offset-transparent transition-all duration-300"
          style={{
            top: targetRect.top,
            left: targetRect.left,
            width: targetRect.width,
            height: targetRect.height,
            boxShadow: "0 0 0 9999px rgba(10, 12, 14, 0.62)",
          }}
        />
      )}

      <div
        id="onboarding-tour-tooltip"
        className={cn(
          "absolute w-[min(100vw-24px,380px)] rounded-2xl border border-border/60 bg-white p-5 shadow-2xl shadow-black/20 transition-opacity duration-200",
          !stepReady && "opacity-0 pointer-events-none",
        )}
        style={{ top: tooltipPos.top, left: tooltipPos.left }}
      >
        <div className="mb-3 flex items-center justify-between gap-3">
          <div className="min-w-0">
            <span className="text-[11px] font-bold uppercase tracking-wide text-emerald-dark">
              Крок {stepIndex + 1} з {steps.length}
            </span>
            {step.section && (
              <span className="mt-0.5 block truncate text-[11px] text-muted">{step.section}</span>
            )}
          </div>
        </div>

        <h2 id="onboarding-tour-title" className="text-[18px] font-black leading-snug tracking-tight text-ink">
          {title}
        </h2>
        <p className="mt-2 text-[13px] leading-relaxed text-muted">{step.description}</p>

        {step.tips && step.tips.length > 0 && (
          <ul className="mt-3 space-y-1.5 rounded-xl bg-surface/80 px-3.5 py-3">
            {step.tips.map(tip => (
              <li key={tip} className="flex gap-2 text-[12px] leading-relaxed text-ink/85">
                <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-emerald" aria-hidden />
                <span>{tip}</span>
              </li>
            ))}
          </ul>
        )}

        <div className="mt-4 flex gap-2">
          {!isFirst && (
            <Button type="button" variant="secondary" size="sm" onClick={goBack} className="flex-1" disabled={!stepReady}>
              Назад
            </Button>
          )}
          <Button
            type="button"
            variant="emerald"
            size="sm"
            showArrow={isLast}
            onClick={goNext}
            className="flex-1"
            disabled={!stepReady}
          >
            {isLast ? "Почати роботу" : "Далі"}
          </Button>
        </div>

        <button
          type="button"
          onClick={handleSkip}
          className="mt-3 w-full rounded-xl py-2.5 text-[13px] font-semibold text-muted transition-colors hover:bg-surface hover:text-ink"
        >
          Розберуся сам
        </button>

        <div className="mt-4 flex justify-center gap-1.5">
          {steps.map((_, i) => (
            <span
              key={i}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === stepIndex ? "w-5 bg-emerald" : "w-1.5 bg-border",
              )}
            />
          ))}
        </div>
      </div>
    </div>,
    document.body,
  );
}
