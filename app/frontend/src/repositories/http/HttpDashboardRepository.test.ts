import { afterEach, describe, expect, it, vi } from "vitest";

import { setTokenProvider } from "@/auth/tokenProvider";
import { HttpDashboardRepository } from "@/repositories/http/HttpDashboardRepository";

describe("HttpDashboardRepository", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("maps the owner-scoped dashboard API response", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          project_name: "isort",
          as_of: "August 10, 2026 · 22:00 UTC",
          coverage: [{ day: "Aug 10", branch: 75, statement: 82 }],
          kpis: [
            {
              label: "Total Experiments",
              value: "1",
              delta: "Owner-scoped records",
              trend: "neutral",
              icon: "experiments",
            },
          ],
          quick_stats: [{ label: "Metric calls", value: "30" }],
          experiments: [
            {
              id: "experiment-1",
              name: "isort GEPA",
              model: "gemini-3.6-flash",
              branch_coverage: 75,
              statement_coverage: 82,
              status: "completed",
              updated_at: "2026-08-10 22:00 UTC",
            },
          ],
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    const snapshot = await new HttpDashboardRepository().getSnapshot();

    expect(snapshot.projectName).toBe("isort");
    expect(snapshot.quickStats[0]).toEqual({ label: "Metric calls", value: "30" });
    expect(snapshot.experiments[0]).toMatchObject({
      branchCoverage: 75,
      statementCoverage: 82,
      status: "completed",
    });
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/dashboard", expect.any(Object));
  });
});
