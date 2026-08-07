"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import * as api from "@/lib/api";
import { ApiError } from "@/lib/api";
import { clearToken, getRememberMePreference, saveLoginCredentials, setToken } from "@/lib/auth-storage";
import { markOnboardingPending } from "@/lib/onboarding";
import type { User } from "@/types/api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  login: (email: string, password: string, remember?: boolean) => Promise<void>;
  sendRegisterCode: (email: string, name: string, password: string) => Promise<void>;
  verifyRegisterCode: (email: string, code: string) => Promise<void>;
  resendRegisterCode: (email: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
  updateProfile: (body: { name?: string; preferred_currency?: string }) => Promise<void>;
  loginWithToken: (token: string, remember?: boolean) => Promise<void>;
  forgotPassword: (email: string) => Promise<void>;
  resetPassword: (token: string, password: string) => Promise<void>;
  sendPhoneCode: (
    phone: string,
    intent: "login" | "register",
    name?: string,
    delivery?: "auto" | "sms",
  ) => Promise<{ message: string; channel?: "sms" | "telegram" }>;
  verifyPhoneCode: (
    phone: string,
    code: string,
    intent: "login" | "register",
    name?: string,
    remember?: boolean,
  ) => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function clearServerSession() {
  try {
    await api.auth.logout();
  } catch {
    /* cookie може вже бути відсутнім */
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [initialized, setInitialized] = useState(false);
  const router = useRouter();

  const refreshUser = useCallback(async () => {
    // Cookie або Bearer — бекенд приймає обидва; не виходимо лише через відсутність localStorage
    try {
      setUser(await api.auth.me());
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        const revoked =
          typeof err.message === "string" &&
          (err.message.includes("Session revoked") || err.message.includes("Session revoked".toLowerCase()));
        await clearServerSession();
        clearToken();
        setUser(null);
        if (revoked && typeof window !== "undefined") {
          sessionStorage.setItem("carbit_session_revoked", "1");
          if (window.location.pathname.startsWith("/app")) {
            window.location.assign("/auth/login?session=revoked");
            return;
          }
        }
      }
    }
  }, []);

  useEffect(() => {
    refreshUser()
      .finally(() => {
        setLoading(false);
        setInitialized(true);
      });
  }, [refreshUser]);

  const login = async (email: string, password: string, remember = true) => {
    const { access_token } = await api.auth.login({ email, password, remember });
    setToken(access_token, remember);
    saveLoginCredentials(email, remember);
    setUser(await api.auth.me());
  };

  const sendRegisterCode = async (email: string, name: string, password: string) => {
    await api.auth.registerSendCode({ email, name, password });
  };

  const verifyRegisterCode = async (email: string, code: string) => {
    const { access_token } = await api.auth.registerVerify({ email, code });
    setToken(access_token, true);
    setUser(await api.auth.me());
    markOnboardingPending();
  };

  const resendRegisterCode = async (email: string) => {
    await api.auth.registerResendCode(email);
  };

  const logout = async () => {
    await clearServerSession();
    clearToken();
    setUser(null);
    // Hard navigation — інакше AppLayout лишається на /app з user=null (вічний лоадер)
    if (typeof window !== "undefined") {
      window.location.assign("/auth/login");
      return;
    }
    router.push("/auth/login");
  };

  const updateProfile = async (body: { name?: string; preferred_currency?: string }) => {
    setUser(await api.auth.updateProfile(body));
  };

  const loginWithToken = async (token: string, remember = getRememberMePreference()) => {
    setToken(token, remember);
    setUser(await api.auth.me());
  };

  const forgotPassword = async (email: string) => {
    await api.auth.forgotPassword(email);
  };

  const resetPassword = async (token: string, password: string) => {
    const { access_token } = await api.auth.resetPassword(token, password);
    setToken(access_token, true);
    setUser(await api.auth.me());
  };

  const sendPhoneCode = async (
    phone: string,
    intent: "login" | "register",
    name?: string,
    delivery: "auto" | "sms" = "auto",
  ) => {
    return api.auth.phoneSendCode({
      phone,
      intent,
      name: name?.trim() || undefined,
      delivery,
    });
  };

  const verifyPhoneCode = async (
    phone: string,
    code: string,
    intent: "login" | "register",
    name?: string,
    remember = true,
  ) => {
    const { access_token } = await api.auth.phoneVerify({
      phone,
      code,
      intent,
      name: name?.trim() || undefined,
      remember,
    });
    setToken(access_token, remember);
    if (intent === "register") {
      markOnboardingPending();
    }
    setUser(await api.auth.me());
  };

  return (
    <AuthContext.Provider value={{
      user, loading, initialized, login, sendRegisterCode, verifyRegisterCode,
      resendRegisterCode, logout, refreshUser, updateProfile,
      loginWithToken, forgotPassword, resetPassword, sendPhoneCode, verifyPhoneCode,
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
