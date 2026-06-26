"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { useAdminAuth, AdminApiError } from "@/contexts/AdminAuthProvider";

export default function AdminLoginPage() {
  const { login } = useAdminAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      await login(username, password);
    } catch (err) {
      setError(err instanceof AdminApiError ? err.message : "Помилка входу");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-ink flex items-center justify-center p-6">
      <div className="w-full max-w-[380px] bg-white rounded-2xl p-8 shadow-2xl">
        <div className="text-[11px] font-bold uppercase tracking-[0.12em] text-muted mb-1">AutoRadar</div>
        <h1 className="text-[24px] font-black text-ink mb-6">Admin Panel</h1>
        <form onSubmit={submit} className="space-y-4">
          <div>
            <label className="block text-[12px] font-semibold text-ink mb-1">Логін</label>
            <input className="auth-input w-full" value={username} onChange={e => setUsername(e.target.value)} required autoComplete="username" />
          </div>
          <div>
            <label className="block text-[12px] font-semibold text-ink mb-1">Пароль</label>
            <input type="password" className="auth-input w-full" value={password} onChange={e => setPassword(e.target.value)} required autoComplete="current-password" />
          </div>
          {error && <p className="text-[13px] text-red-600">{error}</p>}
          <Button type="submit" loading={loading} variant="emerald" size="md" className="w-full">Увійти</Button>
        </form>
      </div>
    </div>
  );
}
