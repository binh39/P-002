export interface AuthUser {
  id: string;
  name: string;
  email: string | null;
  photoUrl: string | null;
  role: string;
}

export type AuthStateListener = (user: AuthUser | null) => void;

export interface AuthService {
  subscribe(listener: AuthStateListener): () => void;
  signIn(): Promise<void>;
  signOut(): Promise<void>;
  getIdToken(): Promise<string | null>;
}
