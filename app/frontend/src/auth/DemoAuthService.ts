import type { AuthService, AuthStateListener, AuthUser } from "@/auth/AuthService";

const DEMO_SESSION_KEY = "promptopt-demo-session";
const demoUser: AuthUser = {
  id: "demo-user",
  name: "Alex Morgan",
  email: "alex.morgan@company.com",
  photoUrl: null,
  role: "Senior Engineer",
};

export class DemoAuthService implements AuthService {
  private listener: AuthStateListener | null = null;
  private user = sessionStorage.getItem(DEMO_SESSION_KEY) === "active" ? demoUser : null;

  subscribe(listener: AuthStateListener) {
    this.listener = listener;
    listener(this.user);
    return () => {
      this.listener = null;
    };
  }

  private activateSession() {
    sessionStorage.setItem(DEMO_SESSION_KEY, "active");
    this.user = demoUser;
    this.listener?.(this.user);
  }

  async signInWithGoogle() {
    this.activateSession();
  }

  async signInWithEmail() {
    this.activateSession();
  }

  async registerWithEmail() {
    this.activateSession();
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
    return null;
  }
}
