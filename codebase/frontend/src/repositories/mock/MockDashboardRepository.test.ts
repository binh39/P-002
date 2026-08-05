import { describe, expect, it } from "vitest";
import { MockDashboardRepository } from "./MockDashboardRepository";

describe("MockDashboardRepository", () => {
  it("returns an isolated dashboard snapshot", async () => {
    const repository = new MockDashboardRepository();
    const first = await repository.getSnapshot();
    first.experiments[0].name = "changed locally";

    const second = await repository.getSnapshot();
    expect(second.experiments[0].name).not.toBe("changed locally");
    expect(second.coverage.length).toBeGreaterThan(0);
  });

  it("supports request cancellation", async () => {
    const controller = new AbortController();
    const request = new MockDashboardRepository().getSnapshot(controller.signal);
    controller.abort();
    await expect(request).rejects.toMatchObject({ name: "AbortError" });
  });
});
