import { getApps, initializeApp } from "firebase/app";
import {
  createUserWithEmailAndPassword,
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut as firebaseSignOut,
  updateProfile,
} from "firebase/auth";

import type { AuthService, AuthStateListener, AuthUser } from "@/auth/AuthService";
import { env } from "@/config/env";

function createAuth() {
  const app = getApps()[0] ?? initializeApp(env.firebase);
  return getAuth(app);
}

interface IdentityResponse {
  id: string;
  name: string | null;
  email: string | null;
  role: "prompt_engineer" | "prompt_reviewer";
  workspace_id: string;
  permissions: string[];
}

async function toAuthUser(
  user: NonNullable<ReturnType<typeof getAuth>["currentUser"]>,
): Promise<AuthUser> {
  const token = await user.getIdToken();
  const response = await fetch(`${env.apiBaseUrl}/me`, {
    headers: { Accept: "application/json", Authorization: `Bearer ${token}` },
  });
  if (!response.ok) throw new Error("Authenticated profile could not be loaded");
  const identity = (await response.json()) as IdentityResponse;
  return {
    id: identity.id,
    name: identity.name ?? identity.email ?? "PromptOpt user",
    email: identity.email,
    photoUrl: user.photoURL,
    role: identity.role,
    workspaceId: identity.workspace_id,
    permissions: identity.permissions,
  };
}

export class FirebaseAuthService implements AuthService {
  private readonly auth = createAuth();
  private readonly provider = new GoogleAuthProvider();
  private listener: AuthStateListener | null = null;
  private registrationInProgress = false;

  subscribe(listener: AuthStateListener) {
    this.listener = listener;
    return onAuthStateChanged(this.auth, (user) => {
      if (!user) return listener(null);
      // Creating a Firebase user emits an auth-state event before the backend
      // has persisted the selected role. Loading /me at that point would infer
      // the default engineer profile and race the onboarding request.
      if (this.registrationInProgress) return;
      void toAuthUser(user)
        .then(listener)
        .catch(() => listener(null));
    });
  }

  async signInWithGoogle() {
    await signInWithPopup(this.auth, this.provider);
  }
  async signInWithEmail(email: string, password: string) {
    await signInWithEmailAndPassword(this.auth, email, password);
  }
  async registerWithEmail(name: string, email: string, password: string, role: AuthUser["role"]) {
    this.registrationInProgress = true;
    try {
      const credential = await createUserWithEmailAndPassword(this.auth, email, password);
      await updateProfile(credential.user, { displayName: name });
      const token = await credential.user.getIdToken();
      const response = await fetch(`${env.apiBaseUrl}/onboarding`, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ name, role }),
      });
      if (!response.ok) throw new Error("Account role could not be saved");
      this.listener?.(await toAuthUser(credential.user));
    } finally {
      this.registrationInProgress = false;
    }
  }
  async sendPasswordReset(email: string) {
    await sendPasswordResetEmail(this.auth, email);
  }
  async signOut() {
    await firebaseSignOut(this.auth);
  }
  async getIdToken() {
    return this.auth.currentUser?.getIdToken() ?? null;
  }
}
