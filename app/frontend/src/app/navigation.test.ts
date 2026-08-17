import { describe, expect, it } from "vitest";

import { currentNavigationId } from "@/app/navigation";

describe("sidebar navigation mapping", () => {
  it.each([
    "/experiments",
    "/experiments/new",
    "/optimization-runs/run-active",
    "/optimization-runs/run-completed",
    "/runs/legacy-run",
  ])("keeps Experiments active for %s", (pathname) => {
    expect(currentNavigationId(pathname)).toBe("experiments");
  });

  it("uses Overview only for dashboard or unknown routes", () => {
    expect(currentNavigationId("/dashboard")).toBe("dashboard");
    expect(currentNavigationId("/unknown")).toBe("dashboard");
  });
});
