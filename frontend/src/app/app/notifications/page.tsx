"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { notifications as notificationsApi } from "@/lib/api";
import { AppEmpty, AppLoading, AppPage, AppSection } from "@/components/layout/AppPage";
import type { Notification } from "@/types/api";
import { timeAgo, cn } from "@/lib/utils";

export default function NotificationsPage() {
  const [items, setItems] = useState<Notification[]>([]);
  const [unread, setUnread] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const data = await notificationsApi.list();
      setItems(data.items);
      setUnread(data.unread);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const markAll = async () => {
    await notificationsApi.markAllRead();
    setItems(prev => prev.map(n => ({ ...n, is_read: true })));
    setUnread(0);
  };

  const markOne = async (id: string) => {
    await notificationsApi.markRead(id);
    setItems(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n));
    setUnread(prev => Math.max(0, prev - 1));
  };

  const seedDemo = async () => {
    setLoading(true);
    await notificationsApi.seedDemo();
    await load();
  };

  if (loading) return <AppLoading />;

  return (
    <AppPage
      title="Сповіщення"
      description={unread > 0 ? `${unread} непрочитаних` : "Всі прочитані"}
      action={
        <div className="flex gap-2">
          {unread > 0 && <Button variant="secondary" size="sm" onClick={markAll}>Прочитати все</Button>}
          {items.length === 0 && <Button variant="primary" size="sm" onClick={seedDemo}>Демо</Button>}
        </div>
      }
    >
      {items.length === 0 ? (
        <AppEmpty>
          <p className="text-muted">Сповіщень поки немає</p>
          <p className="mx-auto mt-2 max-w-sm text-[12px] text-muted/80">
            Створіть пошуковий запит — нові авто з&apos;являться тут і в Telegram.
          </p>
        </AppEmpty>
      ) : (
        <div className="space-y-2">
          {items.map(n => (
            <AppSection
              key={n.id}
              className={cn(
                "cursor-pointer !p-4 transition-colors",
                n.is_read ? "!bg-white opacity-80" : "!bg-emerald-light/20 border-emerald/20",
              )}
              onClick={() => !n.is_read && markOne(n.id)}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[14px] font-semibold text-ink">{n.title}</span>
                    {!n.is_read && <span className="h-2 w-2 shrink-0 rounded-full bg-emerald" />}
                  </div>
                  <p className="mt-1 text-[12px] leading-relaxed text-muted">{n.body}</p>
                  <div className="mt-2 flex items-center gap-2">
                    {n.sent_telegram && <Badge variant="outline">Telegram</Badge>}
                    <span className="text-[11px] text-muted">{timeAgo(n.created_at)}</span>
                  </div>
                </div>
                {n.listing_id && (
                  <Link href={`/app/listing/${n.listing_id}`} className="shrink-0 text-[12px] font-semibold text-emerald-dark hover:underline">
                    →
                  </Link>
                )}
              </div>
            </AppSection>
          ))}
        </div>
      )}
    </AppPage>
  );
}
