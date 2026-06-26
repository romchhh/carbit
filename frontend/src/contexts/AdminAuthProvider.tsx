"use client";

import { createContext, useContext, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { adminApi, AdminApiError } from "@/lib/admin-api";
import { clearAdminToken, getAdminToken, setAdminToken } from "@/lib/admin-storage";

interface AdminAuthContextValue {
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null);

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => !!getAdminToken());
  const router = useRouter();

  const login = useCallback(async (username: string, password: string) => {
    const { access_token } = await adminApi.login(username, password);
    setAdminToken(access_token);
    setIsAuthenticated(true);
    router.push("/admin");
  }, [router]);

  const logout = useCallback(() => {
    clearAdminToken();
    setIsAuthenticated(false);
    router.push("/admin/login");
  }, [router]);

  return (
    <AdminAuthContext.Provider value={{ isAuthenticated, login, logout }}>
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
