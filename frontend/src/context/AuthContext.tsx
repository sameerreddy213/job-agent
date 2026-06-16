import { createContext, useCallback, useContext, useEffect, useState, ReactNode } from "react";

import { AuthApi, LOGOUT_EVENT, tokenStore } from "../lib/api";
import type { User } from "../lib/types";

interface AuthCtx {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const Ctx = createContext<AuthCtx | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const loadMe = async () => {
    if (!tokenStore.access) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      setUser(await AuthApi.me());
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMe();
    const onLogout = () => setUser(null);
    window.addEventListener(LOGOUT_EVENT, onLogout);
    return () => window.removeEventListener(LOGOUT_EVENT, onLogout);
  }, []);

  const login = async (username: string, password: string) => {
    await AuthApi.login(username, password);
    setUser(await AuthApi.me());
  };

  const logout = async () => {
    await AuthApi.logout();
    setUser(null);
  };

  return <Ctx.Provider value={{ user, loading, login, logout }}>{children}</Ctx.Provider>;
}

export function useAuth(): AuthCtx {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
