import { afterEach, describe, expect, it, vi } from "vitest";

import { setTokenProvider } from "@/auth/tokenProvider";
import { HttpTestGenerationRepository } from "@/repositories/http/HttpTestGenerationRepository";

describe("HttpTestGenerationRepository", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("starts a project-wide final suite from the requested immutable prompt snapshot", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "test-run-1",
            experiment_id: "experiment-1",
            prompt_snapshot_id: "experiment-1:baseline",
            prompt_digest: "baseline-digest",
            prompt_role: "baseline",
            status: "queued",
            project_ids: ["sample:isort"],
            scope: "project",
            model: "gemini/gemini-2.5-flash",
            metrics: {
              test_file_count: 0,
              test_count: 0,
              passed: null,
              failed: null,
              skipped: null,
              project_statement_coverage: null,
              project_branch_coverage: null,
              target_statement_coverage: null,
              target_branch_coverage: null,
              target_score: null,
              target_count: 0,
              completed_target_count: 0,
              failed_target_count: 0,
            },
            estimated_cost_usd: 0,
            error_message: null,
            created_at: "2026-08-18T00:00:00Z",
          }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const result = await new HttpTestGenerationRepository().create("experiment-1", {
      promptRole: "baseline",
      idempotencyKey: "prompt-registry-baseline-test-key",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/prompt-registry/experiment-1/test-generation",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          prompt_role: "baseline",
          scope: "project",
          idempotency_key: "prompt-registry-baseline-test-key",
        }),
      }),
    );
    expect(result).toMatchObject({
      id: "test-run-1",
      promptRole: "baseline",
      status: "queued",
      metrics: { projectStatementCoverage: null },
    });
  });
});
