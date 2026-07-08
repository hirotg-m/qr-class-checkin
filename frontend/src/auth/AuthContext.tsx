import { createContext, useContext, useMemo, useState, type ReactNode } from "react";
import type { Role } from "../api/types";

type AuthState = { token: string; role: Role } | null;

type AuthContextValue = {
  auth: AuthState;
  login: (token: string, role: Role) => void;
  logout: () => void;
};

const STORAGE_KEY = "qr-class-checkin.auth";

const AuthContext = createContext<AuthContextValue | null>(null);

function readStoredAuth(): AuthState {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as AuthState;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [auth, setAuth] = useState<AuthState>(() => readStoredAuth());

  const value = useMemo<AuthContextValue>(
    () => ({
      auth,
      login: (token, role) => {
        const next = { token, role };
        setAuth(next);
        localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
      },
      logout: () => {
        setAuth(null);
        localStorage.removeItem(STORAGE_KEY);
      },
    }),
    [auth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
