"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { IconPlus } from "@/components/icons";
import { Button } from "@/components/ui/Button";
import {
  AppEmpty,
  AppLoading,
  AppPage,
} from "@/components/layout/AppPage";
import { MonitorManagePanel } from "@/components/search/MonitorManagePanel";
import { MonitorSearchCard } from "@/components/search/MonitorSearchCard";
import { UpgradeOffer } from "@/components/billing/UpgradeOffer";
import { SubscriptionPitch } from "@/components/billing/SubscriptionPitch";
import { useAuth } from "@/contexts/AuthProvider";
import { getApiErrorMessage, searches as searchesApi } from "@/lib/api";
import { notifyNotificationsChanged } from "@/lib/notifications-events";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import type { SearchQuery } from "@/types/api";

export default function MonitorsPage() {
  const { user } = useAuth();
  const [searches, setSearches] = useState<SearchQuery[]>([]);
  const [loading, setLoading] = useState(true);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [pendingDelete, setPendingDelete] = useState<SearchQuery | null>(null);
  const [toggleError, setToggleError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const items = await searchesApi.list();
        if (cancelled) return;

        const hasNew = items.some(s => (s.new_count || 0) > 0);
        if (hasNew) {
          // Opening the section clears nav badges for new cars.
          setSearches(items.map(s => ({ ...s, new_count: 0 })));
          void searchesApi
            .markAllSeen()
            .then(() => notifyNotificationsChanged())
            .catch(() => {});
        } else {
          setSearches(items);
        }
      } catch {
        if (!cancelled) setSearches([]);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  if (!user) return null;

  const activeCount = searches.filter(s => s.is_active).length;
  const remaining = Math.max(0, user.searches_limit - activeCount);
  const totalNew = searches.reduce((sum, s) => sum + (s.new_count || 0), 0);
  const limitReached = remaining <= 0;

  const setActive = async (search: SearchQuery, active: boolean) => {
    if (search.is_active === active || togglingId) return;
    if (active && remaining <= 0) {
      setToggleError(
        "Ліміт активних моніторингів вичерпано — підвищіть план або поставте інший на паузу.",
      );
      return;
    }
    setToggleError(null);
    setTogglingId(search.id);
    const previous = searches;
    setSearches(list =>
      list.map(item => (item.id === search.id ? { ...item, is_active: active } : item)),
    );
    try {
      const updated = await searchesApi.update(search.id, { is_active: active });
      setSearches(list => list.map(item => (item.id === updated.id ? updated : item)));
    } catch (err) {
      setSearches(previous);
      setToggleError(
        err instanceof Error ? err.message : "Не вдалося змінити статус моніторингу",
      );
    } finally {
      setTogglingId(null);
    }
  };

  const removeSearch = async (search: SearchQuery) => {
    setDeletingId(search.id);
    setToggleError(null);
    try {
      await searchesApi.delete(search.id);
      setSearches(list => list.filter(item => item.id !== search.id));
      if (editingId === search.id) setEditingId(null);
      setPendingDelete(null);
    } catch (err) {
      setToggleError(getApiErrorMessage(err, "Не вдалося видалити моніторинг"));
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <AppPage wide tourId="tour-section-monitors">
      <div className="mb-6 flex items-end justify-between gap-3">
        <div>
          <h1 className="text-[22px] font-black tracking-tight text-ink sm:text-[26px]">
            Мої моніторинги
          </h1>
          <p className="mt-1 text-[13px] text-muted">
            {activeCount} активних
            {remaining > 0 ? ` · ще ${remaining} доступно` : " · ліміт використано"}
            {totalNew > 0 ? ` · ${totalNew} нових авто` : ""}
          </p>
        </div>
        <Link href="/app/dashboard" className="shrink-0">
          <Button variant="emerald" size="sm" className="gap-1.5">
            <IconPlus size={13} /> Новий
          </Button>
        </Link>
      </div>

      {toggleError && (
        <div
          role="alert"
          className="mb-4 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-[13px] text-red-700"
        >
          {toggleError}
        </div>
      )}

      {limitReached ? (
        <UpgradeOffer className="mb-5" title="Ліміт моніторингів вичерпано" />
      ) : remaining <= 2 ? (
        <SubscriptionPitch
          className="mb-5"
          variant="compact"
          planId={user.plan}
          searchesLimit={user.searches_limit}
          searchesUsed={activeCount}
          isTrial={Boolean(user.is_trial_active)}
        />
      ) : user.plan === "free" ? (
        <SubscriptionPitch
          className="mb-5"
          variant="compact"
          planId={user.plan}
          searchesLimit={user.searches_limit}
          searchesUsed={activeCount}
          isTrial={Boolean(user.is_trial_active)}
        />
      ) : null}

      {loading ? (
        <AppLoading />
      ) : searches.length === 0 ? (
        <AppEmpty>
          <p className="text-[15px] font-medium text-ink">Поки немає моніторингів</p>
          <p className="mx-auto mt-2 max-w-sm text-[13px] text-muted">
            Зробіть пошук і натисніть «Зберегти» — поточні авто і всі нові з’являться тут.
          </p>
          <Link href="/app/dashboard" className="mt-4 inline-block">
            <Button variant="emerald" size="sm" className="gap-1.5">
              <IconPlus size={13} /> Налаштувати фільтри
            </Button>
          </Link>
        </AppEmpty>
      ) : (
        <div className="space-y-3 lg:space-y-4">
          {searches.map(s => (
            <div key={s.id}>
              <MonitorSearchCard
                search={s}
                toggling={togglingId === s.id}
                deleting={deletingId === s.id}
                onActiveChange={active => void setActive(s, active)}
                onEdit={() => setEditingId(id => (id === s.id ? null : s.id))}
                onDelete={() => setPendingDelete(s)}
              />
              {editingId === s.id && (
                <div className="mt-2">
                  <MonitorManagePanel
                    search={s}
                    editorOnly
                    onCancel={() => setEditingId(null)}
                    onUpdated={updated => {
                      setSearches(list =>
                        list.map(item => (item.id === updated.id ? updated : item)),
                      );
                      setEditingId(null);
                    }}
                  />
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title={pendingDelete ? `Видалити моніторинг «${pendingDelete.name}»?` : ""}
        description="Збережені авто зникнуть із цього списку."
        confirmLabel="Видалити"
        cancelLabel="Скасувати"
        variant="danger"
        loading={Boolean(pendingDelete && deletingId === pendingDelete.id)}
        onClose={() => {
          if (!deletingId) setPendingDelete(null);
        }}
        onConfirm={() => {
          if (pendingDelete) void removeSearch(pendingDelete);
        }}
      />
    </AppPage>
  );
}
