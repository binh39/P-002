import { afterEach, describe, expect, it, vi } from "vitest";

import { setTokenProvider } from "@/auth/tokenProvider";
import { HttpExperimentRepository } from "@/repositories/http/HttpExperimentRepository";

describe("HttpExperimentRepository", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("maps create and baseline API contracts without fixture fallback", async () => {
    const responses = [
      {
        id: "experiment-1",
        project_id: "project-1",
        name: "isort baseline",
        target_function_ids: ["fn-1"],
        dataset_splits: { train: [], validation: [], test: ["fn-1"] },
        optimization_eligible: false,
        status: "draft",
        baseline_run_id: null,
        created_at: "2026-08-06T00:00:00Z",
        updated_at: "2026-08-06T00:00:00Z",
      },
      {
        id: "run-1",
        experiment_id: "experiment-1",
        status: "baseline_queued",
        target_count: 1,
        coverage_score: null,
        statement_coverage: null,
        branch_coverage: null,
        prompt_digest: null,
        artifact_objects: {},
        target_metrics: {},
        error_message: null,
        created_at: "2026-08-06T00:00:00Z",
        started_at: null,
        finished_at: null,
      },
    ];
    const fetchMock = vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(responses.shift()), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
    vi.stubGlobal("fetch", fetchMock);
    const repository = new HttpExperimentRepository();

    const experiment = await repository.create({
      projectId: "project-1",
      name: "isort baseline",
      targetFunctionIds: ["fn-1"],
    });
    const run = await repository.requestBaseline(experiment.id);

    expect(experiment.projectId).toBe("project-1");
    expect(run.status).toBe("baseline_queued");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/experiments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          project_id: "project-1",
          name: "isort baseline",
          target_function_ids: ["fn-1"],
        }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/experiments/experiment-1/runs",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
