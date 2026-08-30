import type { AuthService, AuthStateListener, AuthUser } from "@/auth/AuthService";

const DEMO_SESSION_KEY = "promptopt-demo-identity";
const engineer: AuthUser = {
  id: "local-engineer",
  name: "Local Engineer",
  email: "engineer@promptopt.dev",
  photoUrl: null,
  role: "prompt_engineer",
  workspaceId: "local-workspace",
  permissions: ["projects:write", "experiments:write", "test_suites:write"],
};
const reviewer: AuthUser = {
  id: "local-reviewer",
  name: "Local Reviewer",
  email: "reviewer@promptopt.dev",
  photoUrl: null,
  role: "prompt_reviewer",
  workspaceId: "local-workspace",
  permissions: ["reviews:read", "reviews:decide", "test_suites:read"],
};

function storedUser() {
  const identity = sessionStorage.getItem(DEMO_SESSION_KEY);
  return identity === "reviewer" ? reviewer : identity === "engineer" ? engineer : null;
}

export class DemoAuthService implements AuthService {
  private listener: AuthStateListener | null = null;
  private user = storedUser();

  subscribe(listener: AuthStateListener) {
    this.listener = listener;
    listener(this.user);
    return () => {
      this.listener = null;
    };
  }

  private activateSession(user: AuthUser) {
    sessionStorage.setItem(
      DEMO_SESSION_KEY,
      user.role === "prompt_reviewer" ? "reviewer" : "engineer",
    );
    this.user = user;
    this.listener?.(this.user);
  }

  async signInWithGoogle() {
    this.activateSession(engineer);
  }

  async signInWithEmail(email: string) {
    this.activateSession(email.trim().toLowerCase() === reviewer.email ? reviewer : engineer);
  }

  async registerWithEmail(
    _name: string,
    _email: string,
    _password: string,
    role: AuthUser["role"],
  ) {
    this.activateSession(role === "prompt_reviewer" ? reviewer : engineer);
  }

  async sendPasswordReset() {
    return Promise.resolve();
  }

  async signOut() {
    sessionStorage.removeItem(DEMO_SESSION_KEY);
    this.user = null;
    this.listener?.(null);
  }

  async getIdToken() {
    if (this.user?.role === "prompt_reviewer") return "dev-reviewer-token";
    return this.user ? "dev-engineer-token" : null;
  }
}
