import { useState } from "react";

import { IC } from "@/components/Icons";

type AuthMode = "login" | "register";
type PendingAction = "email" | "google" | "reset" | null;

interface Props {
  onClearError: () => void;
  onGoogleSignIn: () => Promise<void>;
  onEmailSignIn: (email: string, password: string) => Promise<void>;
  onRegister: (name: string, email: string, password: string) => Promise<void>;
  onPasswordReset: (email: string) => Promise<void>;
  connected: boolean;
  authError?: string | null;
}

export default function Login({
  onClearError,
  onGoogleSignIn,
  onEmailSignIn,
  onRegister,
  onPasswordReset,
  connected,
  authError,
}: Props) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [name, setName] = useState("");
  const [email, setEmail] = useState(connected ? "" : "alex.morgan@company.com");
  const [password, setPassword] = useState(connected ? "" : "demo-password");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pendingAction, setPendingAction] = useState<PendingAction>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const isRegister = mode === "register";
  const isBusy = pendingAction !== null;

  const clearMessages = () => {
    setFormError(null);
    setNotice(null);
    onClearError();
  };

  const switchMode = () => {
    setMode((current) => (current === "login" ? "register" : "login"));
    setPassword(connected ? "" : "demo-password");
    setConfirmPassword("");
    clearMessages();
  };

  const runAction = async (action: PendingAction, callback: () => Promise<void>) => {
    clearMessages();
    setPendingAction(action);
    try {
      await callback();
      return true;
    } catch {
      return false;
    } finally {
      setPendingAction(null);
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    const normalizedEmail = email.trim();
    const normalizedName = name.trim();

    if (isRegister && normalizedName.length < 2) {
      setFormError("Enter your full name.");
      return;
    }
    if (isRegister && password.length < 8) {
      setFormError("Create a password with at least 8 characters.");
      return;
    }
    if (isRegister && password !== confirmPassword) {
      setFormError("Passwords do not match.");
      return;
    }

    await runAction("email", () =>
      isRegister
        ? onRegister(normalizedName, normalizedEmail, password)
        : onEmailSignIn(normalizedEmail, password),
    );
  };

  const handlePasswordReset = async () => {
    const normalizedEmail = email.trim();
    if (!normalizedEmail) {
      setFormError("Enter your email address first.");
      return;
    }

    const sent = await runAction("reset", () => onPasswordReset(normalizedEmail));
    if (sent) setNotice("Password reset instructions have been sent to your email.");
  };

  return (
    <main className="auth-page">
      <div className="auth-decoration" aria-hidden="true">
        <div className="auth-glow auth-glow-top" />
        <div className="auth-glow auth-glow-bottom" />
      </div>

      <div className="auth-container">
        <header className="auth-brand">
          <div className="auth-brand-title">
            <div className="auth-logo">
              <IC.Zap />
            </div>
            <h1>PromptOpt</h1>
          </div>
          <p>AI Prompt Optimization Platform</p>
        </header>

        <section className="auth-card" aria-labelledby="auth-title">
          <div className="auth-card-heading">
            <h2 id="auth-title">{isRegister ? "Register" : "Login"}</h2>
          </div>

          {(formError || authError) && (
            <div className="auth-error" role="alert">
              {formError ?? authError}
            </div>
          )}
          {notice && (
            <div className="auth-notice" role="status">
              {notice}
            </div>
          )}

          <form onSubmit={(event) => void handleSubmit(event)}>
            {isRegister && (
              <div className="auth-field">
                <label htmlFor="auth-name">Full name</label>
                <input
                  id="auth-name"
                  value={name}
                  onChange={(event) => setName(event.target.value)}
                  type="text"
                  autoComplete="name"
                  placeholder="Alex Morgan"
                  required
                  disabled={isBusy}
                />
              </div>
            )}

            <div className="auth-field">
              <label htmlFor="auth-email">Email address</label>
              <input
                id="auth-email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                required
                disabled={isBusy}
              />
            </div>

            <div className="auth-field">
              <div className="auth-field-row">
                <label htmlFor="auth-password">Password</label>
                {!isRegister && (
                  <button
                    className="auth-text-button"
                    type="button"
                    onClick={() => void handlePasswordReset()}
                    disabled={isBusy}
                  >
                    {pendingAction === "reset" ? "Sending…" : "Forgot password?"}
                  </button>
                )}
              </div>
              <input
                id="auth-password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                type="password"
                autoComplete={isRegister ? "new-password" : "current-password"}
                placeholder={isRegister ? "At least 8 characters" : "Enter your password"}
                required
                minLength={isRegister ? 8 : 6}
                disabled={isBusy}
              />
            </div>

            {isRegister && (
              <div className="auth-field">
                <label htmlFor="auth-confirm-password">Confirm password</label>
                <input
                  id="auth-confirm-password"
                  value={confirmPassword}
                  onChange={(event) => setConfirmPassword(event.target.value)}
                  type="password"
                  autoComplete="new-password"
                  placeholder="Re-enter your password"
                  required
                  minLength={8}
                  disabled={isBusy}
                />
              </div>
            )}

            <button className="auth-primary-button" type="submit" disabled={isBusy}>
              {pendingAction === "email"
                ? isRegister
                  ? "Creating account…"
                  : "Logging in…"
                : isRegister
                  ? "Register"
                  : "Login"}
            </button>
          </form>

          <button
            className="auth-switch-button"
            type="button"
            onClick={switchMode}
            disabled={isBusy}
          >
            {isRegister ? "Already have an account? Login" : "Create new account"}
          </button>

          <div className="auth-divider">
            <span />
            <p>or continue with</p>
            <span />
          </div>

          <button
            className="auth-google-button"
            type="button"
            onClick={() => void runAction("google", onGoogleSignIn)}
            disabled={isBusy}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
              <path
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                fill="#4285F4"
              />
              <path
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                fill="#34A853"
              />
              <path
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                fill="#FBBC05"
              />
              <path
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                fill="#EA4335"
              />
            </svg>
            {pendingAction === "google"
              ? "Connecting…"
              : connected
                ? "Sign in with Google"
                : "Continue with demo account"}
          </button>
        </section>

        <p className="auth-legal">
          By signing in, you agree to the <span>Terms of Service</span> and{" "}
          <span>Privacy Policy</span>.
        </p>
      </div>
    </main>
  );
}
