export type UserRole = "prompt_engineer" | "prompt_reviewer";

export interface AuthUser {
  id: string;
  name: string;
  email: string | null;
  photoUrl: string | null;
  role: UserRole;
  workspaceId: string;
  permissions: string[];
}

export type AuthStateListener = (user: AuthUser | null) => void;

export interface AuthService {
  subscribe(listener: AuthStateListener): () => void;
  signInWithGoogle(): Promise<void>;
  signInWithEmail(email: string, password: string): Promise<void>;
  registerWithEmail(name: string, email: string, password: string): Promise<void>;
  sendPasswordReset(email: string): Promise<void>;
  signOut(): Promise<void>;
  getIdToken(): Promise<string | null>;
}
