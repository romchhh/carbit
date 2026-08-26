"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AdminAuthProvider, useAdminAuth } from "@/contexts/AdminAuthProvider";
import { AdminSidebar } from "@/components/admin/AdminSidebar";

function AdminShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-surface lg:flex-row">
      <AdminSidebar />
      <main className="min-w-0 flex-1 overflow-x-auto overflow-y-auto p-4 sm:p-6 lg:p-8">
        {children}
      </main>
    </div>
  );
}

function AdminLoadingShell() {
  return (
    <div className="flex min-h-screen flex-col bg-surface lg:flex-row">
      <div className="hidden w-[220px] shrink-0 bg-ink lg:block" aria-hidden />
      <main className="flex flex-1 items-center justify-center p-6 sm:p-8">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-emerald border-t-transparent" />
      </main>
    </div>
  );
}

function AdminGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, isReady } = useAdminAuth();
  const isLogin = pathname === "/admin/login";

  useEffect(() => {
    if (!isReady) return;
    if (!isLogin && !isAuthenticated) {
      router.replace("/admin/login");
    }
    if (isLogin && isAuthenticated) {
      router.replace("/admin");
    }
  }, [isLogin, isAuthenticated, isReady, router]);

  if (isLogin) return <>{children}</>;

  if (!isReady) return <AdminLoadingShell />;

  if (!isAuthenticated) return <AdminLoadingShell />;

  return <AdminShell>{children}</AdminShell>;
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminGuard>{children}</AdminGuard>
    </AdminAuthProvider>
  );
}
