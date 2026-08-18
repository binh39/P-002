import { afterEach, describe, expect, it, vi } from "vitest";

import { setTokenProvider } from "@/auth/tokenProvider";
import { HttpPromptRegistryRepository } from "@/repositories/http/HttpPromptRegistryRepository";

describe("HttpPromptRegistryRepository", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("maps the experiment-centric prompt registry API contract", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            items: [
              {
                experiment_id: "experiment-1",
                experiment_name: "isort prompt optimization",
                project_ids: ["sample:isort"],
                project_names: ["isort"],
                status: "approved",
                baseline: {
                  id: "experiment-1:baseline",
                  experiment_id: "experiment-1",
                  role: "baseline",
                  origin: "initial_baseline",
                  prompt_digest: "baseline-digest",
                  prompt: { initial: "initial", error: "error" },
                  source_snapshot_digest: "source-digest",
                  dataset_digest: "dataset-digest",
                  split_seed: 7,
                  runner_protocol_version: 3,
                  coverup_model: "gemini/gemini-2.5-flash",
                  optimize_model: "gemini/gemini-2.5-pro",
                  metrics: {
                    score: 0.7,
                    statement_coverage: 0.75,
                    branch_coverage: 0.65,
                    pass_rate: 1,
                  },
                  estimated_cost_usd: null,
                  created_at: "2026-08-18T00:00:00Z",
                },
                optimized: null,
                baseline_metrics: {
                  score: 0.7,
                  statement_coverage: 0.75,
                  branch_coverage: 0.65,
                  pass_rate: 1,
                },
                optimized_metrics: {
                  score: null,
                  statement_coverage: null,
                  branch_coverage: null,
                  pass_rate: null,
                },
                absolute_gain: null,
                created_at: "2026-08-18T00:00:00Z",
                updated_at: "2026-08-18T00:00:00Z",
              },
            ],
            total: 1,
            offset: 0,
            limit: 50,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const result = await new HttpPromptRegistryRepository().list();

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/prompt-registry?limit=50",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
    expect(result.items[0]).toMatchObject({
      experimentId: "experiment-1",
      projectNames: ["isort"],
      baseline: { coverupModel: "gemini/gemini-2.5-flash" },
      baselineMetrics: { statementCoverage: 0.75, branchCoverage: 0.65 },
    });
  });
});
