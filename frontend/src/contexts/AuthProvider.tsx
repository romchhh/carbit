"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import { clearToken, getToken, saveLoginCredentials, setToken } from "@/lib/auth-storage";
import { markOnboardingPending } from "@/lib/onboarding";
import type { User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string, remember?: boolean) => Promise<void>;
  sendRegisterCode: (email: string, name: string, password: string) => Promise<void>;
  verifyRegisterCode: (email: string, code: string) => Promise<void>;
  resendRegisterCode: (email: string) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateProfile: (name: string) => Promise<void>;
  loginWithToken: (token: string) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (token: string, password: string) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      return;
    }

    try {
      setUser(await api.auth.me());
    } catch {
      clearToken();
      setUser(null);
    }
  }, []);

  useEffect(() => {
    refreshUser().finally(() => setLoading(false));
  }, [refreshUser]);

  const login = async (email: string, password: string, remember = true) => {
    const { access_token } = await api.auth.login({ email, password });
    setToken(access_token, remember);
    saveLoginCredentials(email, remember);
    setUser(await api.auth.me());
  };

  const sendRegisterCode = async (email: string, name: string, password: string) => {
    await api.auth.registerSendCode({ email, name, password });
  };

  const verifyRegisterCode = async (email: string, code: string) => {
    const { access_token } = await api.auth.registerVerify({ email, code });
    setToken(access_token);
    setUser(await api.auth.me());
    markOnboardingPending();
  };

  const resendRegisterCode = async (email: string) => {
    await api.auth.registerResendCode(email);
  };

  const logout = () => {
    clearToken();
    setUser(null);
    router.push("/auth/login");
  };

  const updateProfile = async (name: string) => {
    setUser(await api.auth.updateProfile(name));
  };

  const loginWithToken = async (token: string) => {
    setToken(token);
    setUser(await api.auth.me());
  };

  const forgotPassword = async (email: string) => {
    await api.auth.forgotPassword(email);
  };

  const resetPassword = async (token: string, password: string) => {
    const { access_token } = await api.auth.resetPassword(token, password);
    setToken(access_token);
    setUser(await api.auth.me());
  };

  return (
    <AuthContext.Provider value={{
      user, loading, login, sendRegisterCode, verifyRegisterCode,
      resendRegisterCode, logout, refreshUser, updateProfile,
      loginWithToken, forgotPassword, resetPassword,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
