// Contexte d'authentification C-Lab.
//
// Le jeton JWT est conservé dans AsyncStorage et rejoué en en-tête
// Authorization sur chaque appel API. Le quota affiché vient du serveur :
// c'est lui qui fait foi (le compteur local d'avant était contournable en
// vidant le navigateur).

import AsyncStorage from "@react-native-async-storage/async-storage";
import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

const BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL ?? "";
const TOKEN_KEY = "@clab/token/v1";

export type User = {
  user_id: string;
  email: string;
  premium: boolean;
  created_at?: string | null;
};

export type Usage = {
  premium: boolean;
  limit: number | null;
  used: number;
  remaining: number | null;
  can_compute: boolean;
};

type AuthState = {
  ready: boolean;
  token: string | null;
  user: User | null;
  usage: Usage | null;
  signIn: (email: string, password: string) => Promise<void>;
  signUp: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
  refresh: () => Promise<void>;
  changePassword: (current: string, next: string) => Promise<void>;
  /** Appelé après un calcul pour rafraîchir le compteur affiché. */
  noteCalculation: () => void;
};

const AuthCtx = createContext<AuthState | null>(null);

/** Erreur portant le message renvoyé par l'API (déjà en français). */
export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function api<T>(
  path: string,
  init: RequestInit = {},
  token?: string | null,
): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  const text = await res.text();
  let body: unknown = null;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    body = null;
  }
  if (!res.ok) {
    const detail =
      (body as { detail?: string } | null)?.detail ??
      `Erreur ${res.status}`;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [user, setUser] = useState<User | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);

  const applySession = useCallback(
    async (nextToken: string, nextUser: User) => {
      await AsyncStorage.setItem(TOKEN_KEY, nextToken);
      setToken(nextToken);
      setUser(nextUser);
    },
    [],
  );

  const clearSession = useCallback(async () => {
    await AsyncStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setUsage(null);
  }, []);

  const refresh = useCallback(async () => {
    const t = token ?? (await AsyncStorage.getItem(TOKEN_KEY));
    if (!t) {
      setUser(null);
      setUsage(null);
      return;
    }
    try {
      const data = await api<{ user: User; usage: Usage }>(
        "/api/auth/me",
        { method: "GET" },
        t,
      );
      setToken(t);
      setUser(data.user);
      setUsage(data.usage);
    } catch (e) {
      // Jeton expiré ou révoqué : on repart proprement en déconnecté.
      if (e instanceof ApiError && e.status === 401) await clearSession();
    }
  }, [token, clearSession]);

  // Restauration de session au démarrage.
  useEffect(() => {
    (async () => {
      await refresh();
      setReady(true);
    })();
    // Volontairement au montage uniquement.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = useCallback(
    async (email: string, password: string) => {
      const data = await api<{ user: User; token: string }>("/api/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      await applySession(data.token, data.user);
      const u = await api<Usage>("/api/auth/usage", { method: "GET" }, data.token);
      setUsage(u);
    },
    [applySession],
  );

  const signUp = useCallback(
    async (email: string, password: string) => {
      const data = await api<{ user: User; token: string }>(
        "/api/auth/register",
        { method: "POST", body: JSON.stringify({ email, password }) },
      );
      await applySession(data.token, data.user);
      const u = await api<Usage>("/api/auth/usage", { method: "GET" }, data.token);
      setUsage(u);
    },
    [applySession],
  );

  const changePassword = useCallback(
    async (current: string, next: string) => {
      await api(
        "/api/auth/password",
        {
          method: "POST",
          body: JSON.stringify({
            current_password: current,
            new_password: next,
          }),
        },
        token,
      );
    },
    [token],
  );

  const noteCalculation = useCallback(() => {
    // Décrément optimiste pour un retour immédiat, puis resynchronisation
    // sur la valeur du serveur (qui reste la référence).
    setUsage((prev) =>
      prev && !prev.premium && prev.remaining !== null
        ? {
            ...prev,
            used: prev.used + 1,
            remaining: Math.max(prev.remaining - 1, 0),
            can_compute: prev.remaining - 1 > 0,
          }
        : prev,
    );
    void refresh();
  }, [refresh]);

  const value = useMemo<AuthState>(
    () => ({
      ready,
      token,
      user,
      usage,
      signIn,
      signUp,
      signOut: clearSession,
      refresh,
      changePassword,
      noteCalculation,
    }),
    [
      ready,
      token,
      user,
      usage,
      signIn,
      signUp,
      clearSession,
      refresh,
      changePassword,
      noteCalculation,
    ],
  );

  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthCtx);
  if (!ctx) throw new Error("useAuth doit être utilisé dans un <AuthProvider>");
  return ctx;
}

/** Jeton courant, pour les appels hors contexte React (ex. calculs). */
export async function getStoredToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY);
}
