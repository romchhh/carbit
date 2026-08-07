"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { adminApi, AdminApiError, AdminSourceRequest } from "@/lib/admin-api";
import { formatKyivDateTime } from "@/lib/datetime";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/Badge";

const STATUS_OPTIONS = [
  { value: "", label: "Всі статуси" },
  { value: "pending", label: "Очікує" },
  { value: "in_review", label: "На розгляді" },
  { value: "approved", label: "Схвалено" },
  { value: "rejected", label: "Відхилено" },
] as const;

const STATUS_LABELS: Record<string, string> = {
  pending: "Очікує",
  in_review: "На розгляді",
  approved: "Схвалено",
  rejected: "Відхилено",
};

export default function AdminSourceRequestsPage() {
  const [items, setItems] = useState<AdminSourceRequest[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [status, setStatus] = useState("");
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<AdminSourceRequest | null>(null);
  const [editStatus, setEditStatus] = useState("");
  const [adminNote, setAdminNote] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.sourceRequests(page, { status: status || undefined, search });
      setItems(data.items);
      setTotal(data.total);
    } finally {
      setLoading(false);
    }
  }, [page, status, search]);

  useEffect(() => {
    load();
  }, [load]);

  const openItem = (item: AdminSourceRequest) => {
    setSelected(item);
    setEditStatus(item.status);
    setAdminNote(item.admin_note ?? "");
    setError("");
  };

  const save = async () => {
    if (!selected) return;
    setSaving(true);
    setError("");
    try {
      const updated = await adminApi.updateSourceRequest(selected.id, {
        status: editStatus,
        admin_note: adminNote,
      });
      setSelected(updated);
      await load();
    } catch (err) {
      setError(err instanceof AdminApiError ? err.message : "Помилка збереження");
    } finally {
      setSaving(false);
    }
  };

  const pages = Math.max(1, Math.ceil(total / 20));

  return (
    <div className="max-w-[1200px]">
      <h1 className="text-[28px] font-black text-ink mb-1">Заявки на джерела</h1>
      <p className="text-[13px] text-muted mb-6">
        Пропозиції користувачів додати Telegram-канал або сайт до моніторингу · {total} заявок
      </p>

      <div className="flex flex-wrap gap-3 mb-6">
        <input
          className="auth-input flex-1 min-w-[200px] max-w-[320px]"
          placeholder="Пошук URL, коментар, email..."
          value={search}
          onChange={e => {
            setSearch(e.target.value);
            setPage(1);
          }}
        />
        <select
          className="auth-input w-[160px]"
          value={status}
          onChange={e => {
            setStatus(e.target.value);
            setPage(1);
          }}
        >
          {STATUS_OPTIONS.map(opt => (
            <option key={opt.value || "all"} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <div className="bg-white border border-border rounded-xl overflow-hidden">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="border-b border-border bg-surface text-left text-[11px] uppercase tracking-wide text-muted">
                <th className="px-4 py-3 font-semibold">Користувач</th>
                <th className="px-4 py-3 font-semibold">Посилання</th>
                <th className="px-4 py-3 font-semibold">Статус</th>
                <th className="px-4 py-3 font-semibold">Дата</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-muted">
                    Завантаження...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-muted">
                    Заявок немає
                  </td>
                </tr>
              ) : (
                items.map(item => (
                  <tr
                    key={item.id}
                    onClick={() => openItem(item)}
                    className={cn(
                      "border-b border-border last:border-0 cursor-pointer hover:bg-surface/50",
                      selected?.id === item.id && "bg-emerald/5",
                    )}
                  >
                    <td className="px-4 py-3">
                      <div className="font-semibold text-ink">{item.user_name}</div>
                      <div className="text-[11px] text-muted">{item.user_email}</div>
                    </td>
                    <td className="px-4 py-3 max-w-[280px]">
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={e => e.stopPropagation()}
                        className="text-emerald-dark hover:underline break-all line-clamp-2"
                      >
                        {item.url}
                      </a>
                      {item.comment && (
                        <div className="mt-1 text-[11px] text-muted line-clamp-2">{item.comment}</div>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="outline">{STATUS_LABELS[item.status] ?? item.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-[12px] text-muted whitespace-nowrap">
                      {formatKyivDateTime(item.created_at)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>

          {pages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-3 text-[12px]">
              <span className="text-muted">
                Сторінка {page} з {pages}
              </span>
              <div className="flex gap-2">
                <button
                  type="button"
                  disabled={page <= 1}
                  onClick={() => setPage(p => p - 1)}
                  className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40"
                >
                  ←
                </button>
                <button
                  type="button"
                  disabled={page >= pages}
                  onClick={() => setPage(p => p + 1)}
                  className="rounded-lg border border-border px-3 py-1.5 disabled:opacity-40"
                >
                  →
                </button>
              </div>
            </div>
          )}
        </div>

        <aside className="bg-white border border-border rounded-xl p-4 h-fit sticky top-4">
          {selected ? (
            <>
              <h2 className="text-[15px] font-bold text-ink">Заявка</h2>
              <p className="mt-1 text-[12px] text-muted">
                <Link href={`/admin/clients/${selected.user_id}`} className="text-emerald-dark hover:underline">
                  {selected.user_name}
                </Link>
                {" · "}
                {selected.user_email}
              </p>

              <a
                href={selected.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-3 block text-[13px] font-semibold text-emerald-dark hover:underline break-all"
              >
                {selected.url}
              </a>

              {selected.comment && (
                <p className="mt-3 rounded-lg bg-surface px-3 py-2 text-[12px] text-muted leading-relaxed">
                  {selected.comment}
                </p>
              )}

              <div className="mt-4 space-y-3">
                <div>
                  <label className="mb-1 block text-[11px] font-semibold uppercase text-muted">
                    Статус
                  </label>
                  <select
                    className="auth-input w-full"
                    value={editStatus}
                    onChange={e => setEditStatus(e.target.value)}
                  >
                    {STATUS_OPTIONS.filter(o => o.value).map(opt => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-[11px] font-semibold uppercase text-muted">
                    Нотатка адміна
                  </label>
                  <textarea
                    className="auth-input w-full min-h-[80px] resize-y"
                    value={adminNote}
                    onChange={e => setAdminNote(e.target.value)}
                    placeholder="Внутрішній коментар..."
                    maxLength={2000}
                  />
                </div>

                {error && <p className="text-[12px] text-red-600">{error}</p>}

                <button
                  type="button"
                  onClick={save}
                  disabled={saving}
                  className="w-full rounded-xl bg-ink py-2.5 text-[13px] font-bold text-white hover:bg-ink/90 disabled:opacity-50"
                >
                  {saving ? "Збереження..." : "Зберегти"}
                </button>
              </div>
            </>
          ) : (
            <p className="text-[13px] text-muted py-8 text-center">
              Оберіть заявку зі списку, щоб змінити статус або додати нотатку.
            </p>
          )}
        </aside>
      </div>
    </div>
  );
}
