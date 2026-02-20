import { createContext, useContext, useMemo, useState } from "react";
import { apiRequest } from "./api";
import type { LoginResponse, User } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  login: (email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const TOKEN_KEY = "propel_token";
const USER_KEY = "propel_user";

function readUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(readUser());

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      login: async (email: string) => {
        const data = await apiRequest<LoginResponse>("/auth/login", {
          method: "POST",
          body: JSON.stringify({ email })
        });
        setToken(data.access_token);
        setUser(data.user);
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(USER_KEY, JSON.stringify(data.user));
      },
      logout: () => {
        setToken(null);
        setUser(null);
        localStorage.removeItem(TOKEN_KEY);
        localStorage.removeItem(USER_KEY);
      }
    }),
    [token, user]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
