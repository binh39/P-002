/* eslint-disable react-refresh/only-export-components */
import {
  createContext,
  type PropsWithChildren,
  useCallback,
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
  clearError: () => void;
  signInWithGoogle: () => Promise<void>;
  signInWithEmail: (email: string, password: string) => Promise<void>;
  registerWithEmail: (name: string, email: string, password: string) => Promise<void>;
  sendPasswordReset: (email: string) => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

const authErrorMessages: Record<string, string> = {
  "auth/email-already-in-use": "An account already exists for this email address.",
  "auth/invalid-credential": "Incorrect email or password.",
  "auth/invalid-email": "Enter a valid email address.",
  "auth/network-request-failed": "Network error. Check your connection and try again.",
  "auth/operation-not-allowed": "This sign-in method is not enabled yet.",
  "auth/popup-blocked": "The sign-in popup was blocked by your browser.",
  "auth/popup-closed-by-user": "Google sign-in was cancelled.",
  "auth/too-many-requests": "Too many attempts. Please wait and try again.",
  "auth/user-disabled": "This account has been disabled.",
  "auth/weak-password": "Use a stronger password with at least 8 characters.",
};

function getAuthErrorMessage(reason: unknown, fallback: string) {
  if (typeof reason === "object" && reason && "code" in reason) {
    const code = String(reason.code);
    if (authErrorMessages[code]) return authErrorMessages[code];
  }
  return reason instanceof Error ? reason.message : fallback;
}

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

  const runAuthAction = useCallback(
    async (action: (resolvedService: AuthService) => Promise<void>) => {
      setError(null);
      try {
        await action(await service);
      } catch (reason) {
        setError(getAuthErrorMessage(reason, "Authentication failed. Please try again."));
        throw reason;
      }
    },
    [service],
  );

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
      clearError() {
        setError(null);
      },
      async signInWithGoogle() {
        await runAuthAction((resolvedService) => resolvedService.signInWithGoogle());
      },
      async signInWithEmail(email, password) {
        await runAuthAction((resolvedService) => resolvedService.signInWithEmail(email, password));
      },
      async registerWithEmail(name, email, password) {
        await runAuthAction((resolvedService) =>
          resolvedService.registerWithEmail(name, email, password),
        );
      },
      async sendPasswordReset(email) {
        await runAuthAction((resolvedService) => resolvedService.sendPasswordReset(email));
      },
      async signOut() {
        setError(null);
        await (await service).signOut();
      },
    }),
    [error, loading, runAuthAction, service, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const auth = useContext(AuthContext);
  if (!auth) throw new Error("useAuth must be used inside AuthProvider");
  return auth;
}
