import { beforeEach, describe, expect, it, vi } from "vitest";

import { DemoAuthService } from "@/auth/DemoAuthService";

describe("DemoAuthService", () => {
  beforeEach(() => sessionStorage.clear());

  it("signs in independent engineer and reviewer identities and restores reviewer session", async () => {
    const engineerService = new DemoAuthService();
    const engineerListener = vi.fn();
    engineerService.subscribe(engineerListener);
    await engineerService.signInWithEmail("engineer@promptopt.dev");
    expect(engineerListener).toHaveBeenLastCalledWith(
      expect.objectContaining({ id: "local-engineer", role: "prompt_engineer" }),
    );
    expect(await engineerService.getIdToken()).toBe("dev-engineer-token");

    const reviewerService = new DemoAuthService();
    const reviewerListener = vi.fn();
    reviewerService.subscribe(reviewerListener);
    await reviewerService.signInWithEmail("reviewer@promptopt.dev");
    expect(reviewerListener).toHaveBeenLastCalledWith(
      expect.objectContaining({ id: "local-reviewer", role: "prompt_reviewer" }),
    );
    expect(await reviewerService.getIdToken()).toBe("dev-reviewer-token");

    const restored = new DemoAuthService();
    const restoredListener = vi.fn();
    restored.subscribe(restoredListener);
    expect(restoredListener).toHaveBeenCalledWith(
      expect.objectContaining({ id: "local-reviewer", workspaceId: "local-workspace" }),
    );
    await restored.signOut();
    expect(sessionStorage.getItem("promptopt-demo-identity")).toBeNull();
  });
});
