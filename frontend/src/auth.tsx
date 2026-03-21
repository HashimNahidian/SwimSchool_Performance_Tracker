import { createContext, useContext, useEffect, useMemo, useState } from "react";
import {
  AUTH_STATE_EVENT,
  REFRESH_KEY,
  TOKEN_KEY,
  USER_KEY,
  login as apiLogin,
  logout as apiLogout,
  me as apiMe,
  refresh as apiRefresh
} from "./api";
import type { User } from "./types";

interface AuthContextValue {
  user: User | null;
  token: string | null;
  ready: boolean;
  login: (username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function readUser(): User | null {
  const raw = localStorage.getItem(USER_KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as User;
  } catch {
    return null;
  }
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState<User | null>(readUser());
  const [ready, setReady] = useState(false);

  // On mount: validate stored access token, refresh if expired, clear if unrecoverable.
  useEffect(() => {
    const storedToken = localStorage.getItem(TOKEN_KEY);
    const storedRefresh = localStorage.getItem(REFRESH_KEY);

    if (!storedToken) {
      setReady(true);
      return;
    }

    apiMe(storedToken)
      .then((userData) => {
        setUser(userData);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));
        setReady(true);
      })
      .catch(() => {
        if (!storedRefresh) {
          setToken(null);
          setUser(null);
          clearSession();
          setReady(true);
          return;
        }

        apiRefresh(storedRefresh)
          .then(async (data) => {
            setToken(data.access_token);
            localStorage.setItem(TOKEN_KEY, data.access_token);
            localStorage.setItem(REFRESH_KEY, data.refresh_token);
            const userData = await apiMe(data.access_token);
            setUser(userData);
            localStorage.setItem(USER_KEY, JSON.stringify(userData));
          })
          .catch(() => {
            setToken(null);
            setUser(null);
            clearSession();
          })
          .finally(() => setReady(true));
      });
  }, []);

  useEffect(() => {
    function onAuthState(event: Event) {
      const customEvent = event as CustomEvent<
        | { type: "refreshed"; accessToken: string; refreshToken: string }
        | { type: "cleared" }
      >;
      if (customEvent.detail.type === "refreshed") {
        setToken(customEvent.detail.accessToken);
        return;
      }
      setToken(null);
      setUser(null);
      clearSession();
    }

    window.addEventListener(AUTH_STATE_EVENT, onAuthState);
    return () => window.removeEventListener(AUTH_STATE_EVENT, onAuthState);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      token,
      ready,
      login: async (username: string, password: string) => {
        const data = await apiLogin(username, password);
        const userData = await apiMe(data.access_token);
        setToken(data.access_token);
        setUser(userData);
        localStorage.setItem(TOKEN_KEY, data.access_token);
        localStorage.setItem(REFRESH_KEY, data.refresh_token);
        localStorage.setItem(USER_KEY, JSON.stringify(userData));
      },
      logout: () => {
        const rt = localStorage.getItem(REFRESH_KEY);
        if (rt) apiLogout(rt).catch(() => {});
        setToken(null);
        setUser(null);
        clearSession();
      }
    }),
    [token, user, ready]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider");
  return ctx;
}
