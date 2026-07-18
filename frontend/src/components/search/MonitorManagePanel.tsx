"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { ConfirmDialog } from "@/components/ui/ConfirmDialog";
import { SearchFiltersPanel } from "@/components/search/SearchFiltersPanel";
import { getApiErrorMessage, searches as searchesApi } from "@/lib/api";
import {
  buildSearchName,
  fromBackendSearchFilters,
  toBackendSearchFilters,
} from "@/lib/search-filters-api";
import { DEFAULT_FILTERS, type SearchFilterState } from "@/lib/search-catalog";
import type { SearchQuery } from "@/types/api";

type Props = {
  search: SearchQuery;
  onUpdated: (search: SearchQuery) => void;
  onCancel?: () => void;
  /** Лише форма редагування (кнопки дій на картці списку). */
  editorOnly?: boolean;
  onDeleted?: () => void;
};

export function MonitorManagePanel({
  search,
  onUpdated,
  onCancel,
  editorOnly = false,
  onDeleted,
}: Props) {
  const router = useRouter();
  const [editing, setEditing] = useState(editorOnly);
  const [name, setName] = useState(search.name);
  const [filters, setFilters] = useState<SearchFilterState>(DEFAULT_FILTERS);
  const [saving, setSaving] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  useEffect(() => {
    setName(search.name);
    setFilters(fromBackendSearchFilters(search.filters));
    if (editorOnly) setEditing(true);
  }, [search, editorOnly]);

  const saveEdits = async () => {
    setSaving(true);
    setError("");
    setSuccess("");
    try {
      const nextName = name.trim() || buildSearchName(filters);
      const updated = await searchesApi.update(search.id, {
        name: nextName,
        filters: toBackendSearchFilters(filters),
      });
      onUpdated(updated);
      if (!editorOnly) {
        setEditing(false);
        setSuccess("Моніторинг оновлено");
      }
    } catch (err) {
      setError(getApiErrorMessage(err, "Не вдалося зберегти зміни"));
    } finally {
      setSaving(false);
    }
  };

  const toggleActive = async () => {
    setToggling(true);
    setError("");
    setSuccess("");
    try {
      const updated = await searchesApi.update(search.id, {
        is_active: !search.is_active,
      });
      onUpdated(updated);
      setSuccess(updated.is_active ? "Моніторинг знову активний" : "Моніторинг зупинено");
    } catch (err) {
      setError(getApiErrorMessage(err, "Не вдалося змінити статус"));
    } finally {
      setToggling(false);
    }
  };

  const remove = async () => {
    setDeleting(true);
    setError("");
    try {
      await searchesApi.delete(search.id);
      setConfirmDelete(false);
      onDeleted?.();
      router.push("/app/monitors");
    } catch (err) {
      setError(getApiErrorMessage(err, "Не вдалося видалити моніторинг"));
      setDeleting(false);
    }
  };

  return (
    <div className="mb-5 space-y-3">
      {!editorOnly && (
        <div className="flex flex-wrap gap-2">
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() => {
              setEditing(v => !v);
              setError("");
              setSuccess("");
            }}
          >
            {editing ? "Сховати редагування" : "Змінити"}
          </Button>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            loading={toggling}
            onClick={() => void toggleActive()}
          >
            {search.is_active ? "Зупинити" : "Запустити"}
          </Button>
          <Button
            type="button"
            variant="danger"
            size="sm"
            onClick={() => setConfirmDelete(true)}
          >
            Видалити
          </Button>
        </div>
      )}

      {success && (
        <p className="rounded-xl border border-emerald/25 bg-emerald-light/40 px-3 py-2 text-[12px] text-emerald-dark">
          {success}
        </p>
      )}
      {error && (
        <p className="rounded-xl border border-red-100 bg-red-50 px-3 py-2 text-[12px] text-red-600">
          {error}
        </p>
      )}

      {editing && (
        <div className="rounded-2xl border border-border bg-white p-4 sm:p-5">
          <label className="block text-[12px] font-semibold text-ink">
            Назва
            <input
              value={name}
              onChange={e => setName(e.target.value)}
              className="mt-1.5 w-full rounded-xl border border-border bg-surface px-3 py-2.5 text-[14px] text-ink focus:outline-none focus:ring-2 focus:ring-emerald/20"
            />
          </label>

          <div className="mt-4">
            <SearchFiltersPanel
              filters={filters}
              onChange={setFilters}
              onReset={() => setFilters(fromBackendSearchFilters(search.filters))}
              onSearch={() => void saveEdits()}
              searchButtonLabel="Зберегти зміни"
              searchingButtonLabel="Зберігаємо…"
              searching={saving}
            />
          </div>

          {editorOnly && onCancel && (
            <div className="mt-3">
              <Button type="button" variant="secondary" size="sm" onClick={onCancel}>
                Скасувати
              </Button>
            </div>
          )}
        </div>
      )}

      <ConfirmDialog
        open={confirmDelete}
        title={`Видалити моніторинг «${search.name}»?`}
        description="Збережені авто зникнуть із цього списку."
        confirmLabel="Видалити"
        cancelLabel="Скасувати"
        variant="danger"
        loading={deleting}
        onClose={() => {
          if (!deleting) setConfirmDelete(false);
        }}
        onConfirm={() => void remove()}
      />
    </div>
  );
}
