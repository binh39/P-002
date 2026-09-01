import { beforeEach, describe, expect, it, vi } from "vitest";

const firebase = vi.hoisted(() => {
  type MockUser = {
    uid: string;
    photoURL: null;
    getIdToken: () => Promise<string>;
  };
  const user = {
    uid: "reviewer-1",
    photoURL: null,
    getIdToken: vi.fn().mockResolvedValue("firebase-token"),
  };
  return {
    auth: { currentUser: user },
    authStateListener: null as ((user: MockUser | null) => void) | null,
    user,
  };
});

vi.mock("firebase/app", () => ({
  getApps: vi.fn(() => [{}]),
  initializeApp: vi.fn(),
}));

vi.mock("firebase/auth", () => ({
  createUserWithEmailAndPassword: vi.fn(async () => {
    firebase.authStateListener?.(firebase.user);
    return { user: firebase.user };
  }),
  getAuth: vi.fn(() => firebase.auth),
  GoogleAuthProvider: class {},
  onAuthStateChanged: vi.fn((_auth, listener) => {
    firebase.authStateListener = listener;
    return vi.fn();
  }),
  sendPasswordResetEmail: vi.fn(),
  signInWithEmailAndPassword: vi.fn(),
  signInWithPopup: vi.fn(),
  signOut: vi.fn(),
  updateProfile: vi.fn(),
}));

import { FirebaseAuthService } from "@/auth/FirebaseAuthService";

describe("FirebaseAuthService", () => {
  beforeEach(() => {
    firebase.authStateListener = null;
    vi.clearAllMocks();
  });

  it("persists the selected reviewer role before loading the authenticated profile", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: true })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          id: "reviewer-1",
          name: "Review User",
          email: "reviewer@example.com",
          role: "prompt_reviewer",
          workspace_id: "reviewer-1",
          permissions: ["reviews:read", "reviews:decide", "test_suites:read"],
        }),
      });
    vi.stubGlobal("fetch", fetchMock);
    const listener = vi.fn();
    const service = new FirebaseAuthService();
    service.subscribe(listener);

    await service.registerWithEmail(
      "Review User",
      "reviewer@example.com",
      "password123",
      "prompt_reviewer",
    );

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(fetchMock.mock.calls[0][0]).toMatch(/\/onboarding$/);
    expect(fetchMock.mock.calls[0][1]).toEqual(
      expect.objectContaining({
        body: JSON.stringify({ name: "Review User", role: "prompt_reviewer" }),
      }),
    );
    expect(fetchMock.mock.calls[1][0]).toMatch(/\/me$/);
    expect(listener).toHaveBeenCalledTimes(1);
    expect(listener).toHaveBeenCalledWith(
      expect.objectContaining({
        role: "prompt_reviewer",
        permissions: ["reviews:read", "reviews:decide", "test_suites:read"],
      }),
    );
  });
});
