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

function toAuthUser(user: NonNullable<ReturnType<typeof getAuth>["currentUser"]>): AuthUser {
  return {
    id: user.uid,
    name: user.displayName ?? user.email ?? "PromptOpt user",
    email: user.email,
    photoUrl: user.photoURL,
    role: "AI Engineer",
  };
}

export class FirebaseAuthService implements AuthService {
  private readonly auth = createAuth();
  private readonly provider = new GoogleAuthProvider();
  private listener: AuthStateListener | null = null;

  subscribe(listener: AuthStateListener) {
    this.listener = listener;
    return onAuthStateChanged(this.auth, (user) => listener(user ? toAuthUser(user) : null));
  }

  async signInWithGoogle() {
    await signInWithPopup(this.auth, this.provider);
  }
  async signInWithEmail(email: string, password: string) {
    await signInWithEmailAndPassword(this.auth, email, password);
  }
  async registerWithEmail(name: string, email: string, password: string) {
    const credential = await createUserWithEmailAndPassword(this.auth, email, password);
    await updateProfile(credential.user, { displayName: name });
    this.listener?.(toAuthUser(credential.user));
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
