/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  type PropsWithChildren,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import type { AuthService, AuthUser } from "@/auth/AuthService";
import { DemoAuthService } from "@/auth/DemoAuthService";
import { setTokenProvider } from "@/auth/tokenProvider";
import { env } from "@/config/env";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  error: string | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

async function createAuthService(): Promise<AuthService> {
  if (env.authMode === "demo") return new DemoAuthService();
  const { FirebaseAuthService } = await import("@/auth/FirebaseAuthService");
  return new FirebaseAuthService();
}

export function AuthProvider({ children }: PropsWithChildren) {
  const [service] = useState(createAuthService);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    let unsubscribe: () => void = () => undefined;

    void service
      .then((resolvedService) => {
        if (!active) return;
        setTokenProvider(() => resolvedService.getIdToken());
        unsubscribe = resolvedService.subscribe((nextUser) => {
          setUser(nextUser);
          setLoading(false);
        });
      })
      .catch((reason: unknown) => {
        if (!active) return;
        setError(
          reason instanceof Error ? reason.message : "Authentication could not be initialized",
        );
        setLoading(false);
      });

    return () => {
      active = false;
      unsubscribe();
    };
  }, [service]);

  const value = useMemo<AuthContextValue>(
    () => ({
      user,
      loading,
      error,
      async signIn() {
        setError(null);
        try {
          await (await service).signIn();
        } catch (reason) {
          const message = reason instanceof Error ? reason.message : "Sign-in failed";
          setError(message);
          throw reason;
        }
      },
      async signOut() {
        setError(null);
        await (await service).signOut();
      },
    }),
    [error, loading, service, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside AuthProvider");
  return auth;
}
