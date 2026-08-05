import { getApps, initializeApp } from "firebase/app";
import {
  getAuth,
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithPopup,
  signOut as firebaseSignOut,
} from "firebase/auth";

import type { AuthService, AuthStateListener } from "@/auth/AuthService";
import { env } from "@/config/env";

function createAuth() {
  const app = getApps()[0] ?? initializeApp(env.firebase);
  return getAuth(app);
}

export class FirebaseAuthService implements AuthService {
  private readonly auth = createAuth();
  private readonly provider = new GoogleAuthProvider();

  subscribe(listener: AuthStateListener) {
    return onAuthStateChanged(this.auth, (user) =>
      listener(
        user
          ? {
              id: user.uid,
              name: user.displayName ?? user.email ?? "PromptOpt user",
              email: user.email,
              photoUrl: user.photoURL,
              role: "AI Engineer",
            }
          : null,
      ),
    );
  }

  async signIn() {
    await signInWithPopup(this.auth, this.provider);
  }
  async signOut() {
    await firebaseSignOut(this.auth);
  }
  async getIdToken() {
    return this.auth.currentUser?.getIdToken() ?? null;
  }
}
