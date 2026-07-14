"use client";

import { createContext, useContext, useState, useCallback, useEffect } from "react";
import { useRouter } from "next/navigation";
import { adminApi, AdminApiError } from "@/lib/admin-api";
import { clearAdminToken, getAdminToken, setAdminToken } from "@/lib/admin-storage";

interface AdminAuthContextValue {
  isAuthenticated: boolean;
  isReady: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null);

async function clearServerAdminSession() {
  try {
    await adminApi.logout();
  } catch {
    /* ignore */
  }
}

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await adminApi.me();
        if (!cancelled) setIsAuthenticated(true);
      } catch (err) {
        if (err instanceof AdminApiError && (err.status === 401 || err.status === 403)) {
          await clearServerAdminSession();
          clearAdminToken();
          if (!cancelled) setIsAuthenticated(false);
        } else {
          // Мережева помилка — не викидаємо з сесії лише через storage
          if (!cancelled) setIsAuthenticated(!!getAdminToken());
        }
      } finally {
        if (!cancelled) setIsReady(true);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await adminApi.login(username, password);
    setAdminToken(access_token);
    setIsAuthenticated(true);
    router.push("/admin");
  }, [router]);

  const logout = useCallback(async () => {
    await clearServerAdminSession();
    clearAdminToken();
    setIsAuthenticated(false);
    router.push("/admin/login");
  }, [router]);

  return (
    <AdminAuthContext.Provider value={{ isAuthenticated, isReady, login, logout }}>
      {children}
    </AdminAuthContext.Provider>
  );
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext);
  if (!ctx) throw new Error("useAdminAuth must be used within AdminAuthProvider");
  return ctx;
}

export { AdminApiError };
