"use client";

import Link from "next/link";
import { Suspense, useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AppPage, AppSection } from "@/components/layout/AppPage";
import {
  CompareEmptyState,
  ListingCompareTable,
} from "@/components/listings/ListingCompareTable";
import { IconShare } from "@/components/icons";
import { useAuth } from "@/contexts/AuthProvider";
import { useListingCompare } from "@/hooks/useListingCompare";
import { ApiError, comparisons as comparisonsApi, listings as listingsApi } from "@/lib/api";
import {
  MAX_COMPARE,
  buildCompareShareUrl,
  replaceCompareListings,
} from "@/lib/listing-compare";
import type { Listing, SavedComparison } from "@/types/api";

function ComparePageInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { user } = useAuth();
  const { items, count, remove, clear, refresh } = useListingCompare();
  const [saved, setSaved] = useState<SavedComparison[]>([]);
  const [loadingRemote, setLoadingRemote] = useState(false);
  const [remoteError, setRemoteError] = useState<string | null>(null);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [shareMessage, setShareMessage] = useState<string | null>(null);
  const [lastShareId, setLastShareId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const loadSaved = useCallback(async () => {
    try {
      setSaved(await comparisonsApi.list());
    } catch {
      setSaved([]);
    }
  }, []);

  useEffect(() => {
    if (!user) {
      setSaved([]);
      return;
    }
    void loadSaved();
  }, [loadSaved, user]);

  useEffect(() => {
    const idsParam = searchParams.get("ids");
    const shareParam = searchParams.get("share");
    if (!idsParam && !shareParam) return;

    let cancelled = false;
    (async () => {
      setLoadingRemote(true);
      setRemoteError(null);
      try {
        if (shareParam) {
          const data = await comparisonsApi.getShare(shareParam);
          if (cancelled) return;
          replaceCompareListings(data.listings);
          refresh();
          setLastShareId(data.share_id);
        } else if (idsParam) {
          const ids = idsParam.split(",").map(s => s.trim()).filter(Boolean).slice(0, MAX_COMPARE);
          const fetched = await listingsApi.batch(ids);
          if (cancelled) return;
          const map = new Map(fetched.map(item => [item.id, item]));
          const ordered = ids.map(id => map.get(id)).filter((item): item is Listing => Boolean(item));
          if (ordered.length === 0) {
            setRemoteError("Не вдалося завантажити авто за посиланням");
          } else {
            replaceCompareListings(ordered);
            refresh();
          }
        }
        router.replace("/app/compare", { scroll: false });
      } catch (err) {
        if (!cancelled) {
          setRemoteError(err instanceof ApiError ? err.message : "Помилка завантаження порівняння");
        }
      } finally {
        if (!cancelled) setLoadingRemote(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [searchParams, router, refresh]);

  const handleSave = async () => {
    if (count < 2) return;
    setSaving(true);
    setSaveMessage(null);
    try {
      const name = window.prompt("Назва списку порівняння", `Порівняння ${new Date().toLocaleDateString("uk-UA")}`);
      if (name === null) return;
      const created = await comparisonsApi.create({
        name: name.trim() || undefined,
        listing_ids: items.map(item => item.id),
      });
      setLastShareId(created.share_id);
      setSaveMessage("Збережено в акаунті");
      await loadSaved();
    } catch (err) {
      setSaveMessage(err instanceof ApiError ? err.message : "Не вдалося зберегти");
    } finally {
      setSaving(false);
    }
  };

  const handleShare = async () => {
    if (count < 2) return;
    let shareId = lastShareId;
    if (!shareId && user) {
      try {
        const created = await comparisonsApi.create({
          listing_ids: items.map(item => item.id),
        });
        shareId = created.share_id;
        setLastShareId(shareId);
        await loadSaved();
      } catch {
        shareId = null;
      }
    }
    const url = buildCompareShareUrl(items, shareId);
    try {
      await navigator.clipboard.writeText(url);
      setShareMessage("Посилання скопійовано");
    } catch {
      setShareMessage(url);
    }
    window.setTimeout(() => setShareMessage(null), 4000);
  };

  const loadSavedComparison = async (id: string) => {
    setLoadingRemote(true);
    setRemoteError(null);
    try {
      const data = await comparisonsApi.get(id);
      replaceCompareListings(data.listings);
      refresh();
      setLastShareId(data.share_id);
    } catch (err) {
      setRemoteError(err instanceof ApiError ? err.message : "Не вдалося завантажити");
    } finally {
      setLoadingRemote(false);
    }
  };

  const deleteSaved = async (id: string) => {
    await comparisonsApi.remove(id);
    await loadSaved();
  };

  return (
    <AppPage
      wide
      title="Порівняння авто"
      description={`Оберіть до ${MAX_COMPARE} оголошень у пошуку — порівняйте ціну, пробіг, двигун і джерела в одній таблиці.`}
      action={
        count > 0 ? (
          <div className="flex flex-wrap items-center gap-2">
            {count >= 2 && (
              <>
                <button
                  type="button"
                  onClick={() => void handleShare()}
                  className="inline-flex items-center gap-1.5 rounded-xl border border-border px-3 py-2 text-[12px] font-semibold text-ink hover:bg-surface"
                >
                  <IconShare size={14} />
                  Поділитися
                </button>
                {user && (
                  <button
                    type="button"
                    onClick={() => void handleSave()}
                    disabled={saving}
                    className="rounded-xl border border-emerald/40 bg-emerald/5 px-3 py-2 text-[12px] font-semibold text-emerald-dark hover:bg-emerald/10 disabled:opacity-50"
                  >
                    {saving ? "Збереження..." : "Зберегти в акаунті"}
                  </button>
                )}
              </>
            )}
            <button
              type="button"
              onClick={clear}
              className="rounded-xl border border-border px-3 py-2 text-[12px] font-semibold text-muted hover:bg-surface hover:text-ink"
            >
              Очистити все
            </button>
          </div>
        ) : undefined
      }
    >
      {(loadingRemote || remoteError || saveMessage || shareMessage) && (
        <div className="mb-4 space-y-2">
          {loadingRemote && (
            <p className="rounded-xl bg-surface px-4 py-3 text-[13px] text-muted">Завантаження порівняння…</p>
          )}
          {remoteError && (
            <p className="rounded-xl bg-red-50 px-4 py-3 text-[13px] text-red-600">{remoteError}</p>
          )}
          {saveMessage && (
            <p className="rounded-xl bg-emerald/10 px-4 py-3 text-[13px] text-emerald-dark">{saveMessage}</p>
          )}
          {shareMessage && (
            <p className="rounded-xl bg-surface px-4 py-3 text-[13px] text-muted break-all">{shareMessage}</p>
          )}
        </div>
      )}

      {user && saved.length > 0 && (
        <AppSection className="mb-4 !py-3">
          <p className="text-[12px] font-bold uppercase tracking-wide text-muted">Збережені списки</p>
          <ul className="mt-2 flex flex-wrap gap-2">
            {saved.map(item => (
              <li key={item.id} className="flex items-center gap-1 rounded-full border border-border bg-white pl-3 pr-1 py-1">
                <button
                  type="button"
                  onClick={() => void loadSavedComparison(item.id)}
                  className="text-[12px] font-semibold text-ink hover:text-emerald-dark"
                >
                  {item.name}
                  <span className="ml-1 text-muted">({item.listing_ids.length})</span>
                </button>
                <button
                  type="button"
                  onClick={() => void deleteSaved(item.id)}
                  className="rounded-full px-2 py-0.5 text-[11px] text-muted hover:bg-red-50 hover:text-red-600"
                  aria-label="Видалити"
                >
                  ×
                </button>
              </li>
            ))}
          </ul>
        </AppSection>
      )}

      {count === 0 ? (
        <CompareEmptyState />
      ) : count === 1 ? (
        <AppSection>
          <p className="text-[14px] font-semibold text-ink">Додайте ще одне авто</p>
          <p className="mt-2 text-[13px] text-muted">
            Для порівняння потрібно мінімум 2 оголошення. Поверніться до{" "}
            <Link href="/app/dashboard" className="font-semibold text-emerald-dark hover:underline">
              пошуку
            </Link>{" "}
            і натисніть іконку ваг на іншій картці.
          </p>
          <div className="mt-6">
            <ListingCompareTable listings={items} onRemove={remove} />
          </div>
        </AppSection>
      ) : (
        <AppSection className="!p-3 sm:!p-4">
          <ListingCompareTable listings={items} onRemove={remove} />
        </AppSection>
      )}
    </AppPage>
  );
}

export default function ComparePage() {
  return (
    <Suspense
      fallback={
        <div className="flex justify-center py-16">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
        </div>
      }
    >
      <ComparePageInner />
    </Suspense>
  );
}
