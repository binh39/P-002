import { afterEach, describe, expect, it, vi } from "vitest";

import { setTokenProvider } from "@/auth/tokenProvider";
import { HttpExperimentRepository } from "@/repositories/http/HttpExperimentRepository";
import { HttpPromptVersionRepository } from "@/repositories/http/HttpPromptVersionRepository";

describe("HttpExperimentRepository", () => {
  afterEach(() => {
    setTokenProvider(async () => null);
    vi.unstubAllGlobals();
  });

  it("maps the create API contract without fixture fallback", async () => {
    const responses = [
      {
        id: "experiment-1",
        project_id: "project-1",
        project_ids: ["project-1"],
        name: "isort baseline",
        target_function_ids: ["fn-1"],
        dataset_splits: { train: [], validation: [], test: ["fn-1"] },
        sampling_method: "random",
        max_targets: null,
        split_seed: 7,
        split_percentages: { train: 60, validation: 20, test: 20 },
        settings: {
          coverup_model: "vertex_ai/gemini-3.6-flash",
          optimize_model: "vertex_ai/gemini-3.6-flash",
          max_attempts: 3,
          repeat_tests: 2,
          max_concurrency: 10,
          rate_limit: null,
          pytest_args: "",
          max_metric_calls: 30,
          evaluation_replicates: 1,
          reflection_minibatch_size: 3,
          reflection_temperature: 0.7,
        },
        optimization_eligible: false,
        status: "draft",
        baseline_run_id: null,
        optimization_run_id: null,
        comparison_run_id: null,
        prompt_version_id: null,
        created_at: "2026-08-06T00:00:00Z",
        updated_at: "2026-08-06T00:00:00Z",
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
      projectIds: ["project-1"],
      name: "isort baseline",
      samplingMethod: "random",
      maxTargets: null,
      randomSeed: 7,
      splitPercentages: { train: 60, validation: 20, test: 20 },
      manualSplits: null,
      baselinePrompt: null,
      settings: {
        coverupModel: "vertex_ai/gemini-3.6-flash",
        optimizeModel: "vertex_ai/gemini-3.6-flash",
        maxAttempts: 3,
        repeatTests: 2,
        maxConcurrency: 10,
        rateLimit: null,
        pytestArgs: "",
        budgetMode: "custom",
        maxMetricCalls: 30,
        evaluationReplicates: 1,
        reflectionMinibatchSize: 3,
        reflectionTemperature: 0.7,
      },
    });
    expect(experiment.projectId).toBe("project-1");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/experiments",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          project_ids: ["project-1"],
          name: "isort baseline",
          sampling_method: "random",
          max_targets: null,
          random_seed: 7,
          split_percentages: { train: 60, validation: 20, test: 20 },
          manual_splits: null,
          baseline_prompt: null,
          settings: {
            coverup_model: "vertex_ai/gemini-3.6-flash",
            optimize_model: "vertex_ai/gemini-3.6-flash",
            max_attempts: 3,
            repeat_tests: 2,
            max_concurrency: 10,
            rate_limit: null,
            pytest_args: "",
            max_metric_calls: 30,
            evaluation_replicates: 1,
            reflection_minibatch_size: 3,
            reflection_temperature: 0.7,
          },
        }),
      }),
    );
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("starts and maps an optimization run", async () => {
    const response = {
      id: "optimization-1",
      experiment_id: "experiment-1",
      status: "optimization_queued",
      parent_prompt_digest: "parent-digest",
      candidate_prompt: null,
      candidate_prompt_digest: null,
      baseline_validation_score: null,
      candidate_validation_score: null,
      candidate_count: 0,
      metric_calls: 0,
      artifact_objects: {},
      error_message: null,
      created_at: "2026-08-06T00:00:00Z",
      started_at: null,
      finished_at: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await new HttpExperimentRepository().requestOptimization("experiment-1");

    expect(run.id).toBe("optimization-1");
    expect(run.parentPromptDigest).toBe("parent-digest");
    expect(run.status).toBe("optimization_queued");
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/experiments/experiment-1/optimize",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("cancels an active optimization through the API", async () => {
    const response = {
      id: "optimization-1",
      experiment_id: "experiment-1",
      status: "cancelled",
      parent_prompt_digest: "parent-digest",
      candidate_prompt: null,
      candidate_prompt_digest: null,
      baseline_validation_score: 0.2,
      candidate_validation_score: null,
      candidate_count: 0,
      metric_calls: 5,
      final_validation: {},
      artifact_objects: { "evolution.json": "private/evolution.json" },
      error_message: null,
      created_at: "2026-08-06T00:00:00Z",
      started_at: "2026-08-06T00:00:01Z",
      finished_at: "2026-08-06T00:00:30Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await new HttpExperimentRepository().cancelOptimization("optimization-1");

    expect(run.status).toBe("cancelled");
    expect(run.artifacts).toEqual(["evolution.json"]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/experiments/optimization-runs/optimization-1/cancel",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("resumes a paused optimization through the API", async () => {
    const response = {
      id: "optimization-1",
      experiment_id: "experiment-1",
      status: "optimization_queued",
      parent_prompt_digest: "parent-digest",
      candidate_prompt: null,
      candidate_prompt_digest: null,
      baseline_validation_score: null,
      candidate_validation_score: null,
      candidate_count: 0,
      metric_calls: 5,
      final_validation: {},
      artifact_objects: {},
      error_message: null,
      pause_reason: null,
      paused_at: "2026-08-06T00:00:30Z",
      resume_count: 1,
      max_concurrency: 3,
      created_at: "2026-08-06T00:00:00Z",
      started_at: "2026-08-06T00:00:01Z",
      finished_at: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await new HttpExperimentRepository().resumeOptimization("optimization-1", 3);

    expect(run.status).toBe("optimization_queued");
    expect(run.resumeCount).toBe(1);
    expect(run.maxConcurrency).toBe(3);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/experiments/optimization-runs/optimization-1/resume",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ max_concurrency: 3 }),
      }),
    );
  });

  it("deletes an experiment through the authenticated API", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await new HttpExperimentRepository().delete("experiment-1");

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/experiments/experiment-1",
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("starts and maps a paired comparison run", async () => {
    const response = {
      id: "comparison-1",
      experiment_id: "experiment-1",
      optimization_run_id: "optimization-1",
      status: "in_review",
      baseline_prompt_digest: "parent-digest",
      candidate_prompt_digest: "candidate-digest",
      test_target_ids: ["fn-1"],
      replicate_count: 2,
      baseline_metrics: { score: 0.2, pass_rate: 1, sample_count: 2 },
      candidate_metrics: {
        score: 0.7,
        pass_rate: 1,
        sample_count: 2,
        flaky_targets: [],
      },
      absolute_gain: 0.5,
      relative_gain: 2.5,
      promotion_eligible: true,
      decision_reason: "Candidate improved locked-test coverage and passed all hard gates",
      artifact_objects: { "final_validation.json": "private/object" },
      prompt_version_id: "version-1",
      error_message: null,
      created_at: "2026-08-06T00:00:00Z",
      started_at: "2026-08-06T00:00:01Z",
      finished_at: "2026-08-06T00:01:00Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(response), {
        status: 202,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    const run = await new HttpExperimentRepository().requestComparison("experiment-1");

    expect(run.promotionEligible).toBe(true);
    expect(run.candidateMetrics.score).toBe(0.7);
    expect(run.artifacts).toEqual(["final_validation.json"]);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/experiments/experiment-1/compare",
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("lists and reviews prompt versions through the authenticated API", async () => {
    const version = {
      id: "version-1",
      experiment_id: "experiment-1",
      comparison_run_id: "comparison-1",
      parent_prompt_digest: "baseline-digest",
      prompt_digest: "candidate-digest",
      prompt: { system: "Generate robust tests." },
      status: "in_review",
      reviewer_id: null,
      review_comment: "",
      reviewed_at: null,
      created_at: "2026-08-06T00:00:00Z",
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ items: [version], total: 1, offset: 0, limit: 50 }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ ...version, status: "approved", review_comment: "Looks good" }),
          {
            status: 200,
            headers: { "Content-Type": "application/json" },
          },
        ),
      );
    vi.stubGlobal("fetch", fetchMock);
    const repository = new HttpPromptVersionRepository();

    const listed = await repository.list("in_review");
    const reviewed = await repository.review("version-1", "approve", "Looks good");

    expect(listed.items[0].promptDigest).toBe("candidate-digest");
    expect(reviewed.status).toBe("approved");
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      "/api/v1/reviews?limit=50&status=in_review",
      expect.anything(),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      "/api/v1/prompt-versions/version-1/approve",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ comment: "Looks good" }),
      }),
    );
  });
});
