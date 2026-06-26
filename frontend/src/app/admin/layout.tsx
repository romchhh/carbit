"use client";

import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { AdminAuthProvider, useAdminAuth } from "@/contexts/AdminAuthProvider";
import { AdminSidebar } from "@/components/admin/AdminSidebar";
import { getAdminToken } from "@/lib/admin-storage";

function AdminGuard({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated } = useAdminAuth();
  const isLogin = pathname === "/admin/login";

  useEffect(() => {
    const hasToken = !!getAdminToken();
    if (!isLogin && !hasToken && !isAuthenticated) {
      router.replace("/admin/login");
    }
    if (isLogin && hasToken) {
      router.replace("/admin");
    }
  }, [isLogin, isAuthenticated, router]);

  if (isLogin) return <>{children}</>;

  if (!getAdminToken() && !isAuthenticated) return null;

  return (
    <div className="min-h-screen flex bg-surface">
      <AdminSidebar />
      <main className="flex-1 p-8 overflow-auto">{children}</main>
    </div>
  );
}

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <AdminAuthProvider>
      <AdminGuard>{children}</AdminGuard>
    </AdminAuthProvider>
  );
}
