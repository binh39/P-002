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

  it("lists only the final test-generation runs returned by the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            items: [],
            total: 0,
            offset: 0,
            limit: 100,
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const result = await new HttpTestGenerationRepository().list();

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/test-generation-runs?limit=100",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
    expect(result).toMatchObject({ items: [], total: 0, limit: 100 });
  });

  it("sends the named suite target-selection configuration to the API", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            id: "test-run-configured",
            experiment_id: "experiment-1",
            name: "Branch coverage regression",
            prompt_snapshot_id: "experiment-1:optimized",
            prompt_digest: "optimized-digest",
            prompt_role: "optimized",
            status: "queued",
            project_ids: ["sample:isort"],
            sampling_method: "most_branches",
            runtime_environment_id: "sample-runtime",
            source_snapshot_digest: "source-digest",
            dataset_digest: "dataset-digest",
            scope: "project",
            source_files: [],
            function_ids: [],
            target_ids: [],
            model: "google/gemini-2.5-flash",
            random_seed: 23,
            repeat_tests: 5,
            max_attempts: 3,
            max_concurrency: 10,
            rate_limit: null,
            cost_ceiling_usd: null,
            runner_protocol_version: 1,
            metrics: {},
            estimated_cost_usd: 0,
            token_usage: {},
            artifact_objects: {},
            error_message: null,
            created_at: "2026-08-18T00:00:00Z",
            started_at: null,
            finished_at: null,
          }),
          { status: 202, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    await new HttpTestGenerationRepository().create("experiment-1", {
      promptRole: "optimized",
      name: "Branch coverage regression",
      projectIds: ["sample:isort"],
      samplingMethod: "most_branches",
      functionCount: 24,
      model: "google/gemini-2.5-flash",
      randomSeed: 23,
      idempotencyKey: "configured-test-suite-key",
    });

    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/prompt-registry/experiment-1/test-generation",
      expect.objectContaining({
        body: JSON.stringify({
          prompt_role: "optimized",
          name: "Branch coverage regression",
          project_ids: ["sample:isort"],
          sampling_method: "most_branches",
          function_count: 24,
          function_ids: undefined,
          model: "google/gemini-2.5-flash",
          random_seed: 23,
          scope: "project",
          idempotency_key: "configured-test-suite-key",
        }),
      }),
    );
  });

  it("retrieves a run and downloads its owner-scoped artifact", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValueOnce(
          new Response(
            JSON.stringify({
              id: "test-run-1",
              experiment_id: "experiment-1",
              prompt_snapshot_id: "experiment-1:baseline",
              prompt_digest: "baseline-digest",
              prompt_role: "baseline",
              status: "completed",
              project_ids: ["sample:isort"],
              source_snapshot_digest: "source-digest",
              dataset_digest: "dataset-digest",
              scope: "project",
              source_files: [],
              function_ids: [],
              target_ids: ["target-1"],
              model: "gemini/gemini-2.5-flash",
              random_seed: 7,
              repeat_tests: 1,
              max_attempts: 3,
              max_concurrency: 5,
              rate_limit: null,
              cost_ceiling_usd: null,
              runner_protocol_version: 1,
              metrics: {
                test_file_count: 1,
                test_count: 2,
                passed: 2,
                failed: 0,
                skipped: 0,
                project_statement_coverage: 0.7,
                project_branch_coverage: 0.6,
                target_statement_coverage: 0.8,
                target_branch_coverage: 0.7,
                target_score: 0.75,
                target_count: 1,
                completed_target_count: 1,
                failed_target_count: 0,
              },
              estimated_cost_usd: 0.01,
              token_usage: { input_tokens: 10, output_tokens: 20 },
              artifact_objects: { manifest: "private/object" },
              error_message: null,
              created_at: "2026-08-18T00:00:00Z",
              started_at: "2026-08-18T00:00:01Z",
              finished_at: "2026-08-18T00:00:02Z",
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        )
        .mockResolvedValueOnce(new Response("artifact", { status: 200 })),
    );
    const repository = new HttpTestGenerationRepository();

    const run = await repository.get("test-run-1");
    const artifact = await repository.downloadArtifact("test-run-1", "manifest");

    expect(run).toMatchObject({
      sourceSnapshotDigest: "source-digest",
      maxAttempts: 3,
      artifactObjects: { manifest: "private/object" },
    });
    expect(await artifact.text()).toBe("artifact");
    expect(fetch).toHaveBeenLastCalledWith(
      "/api/v1/test-generation-runs/test-run-1/artifacts/manifest",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
  });

  it("requests the manifest viewer through the dedicated owner-scoped endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ metrics: { test_count: 2 } }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const manifest = await new HttpTestGenerationRepository().getManifest("test-run-1");

    expect(manifest).toEqual({ metrics: { test_count: 2 } });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/test-generation-runs/test-run-1/artifacts/manifest/content",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
  });

  it("requests indexed text artifacts through the bounded content endpoint", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(
          JSON.stringify({
            artifact_name: "file-generated-test-1",
            content: "def test_x(): pass",
          }),
          { status: 200, headers: { "Content-Type": "application/json" } },
        ),
      ),
    );

    const result = await new HttpTestGenerationRepository().getTextArtifact(
      "test-run-1",
      "file-generated-test-1",
    );

    expect(result).toEqual({
      artifactName: "file-generated-test-1",
      content: "def test_x(): pass",
    });
    expect(fetch).toHaveBeenCalledWith(
      "/api/v1/test-generation-runs/test-run-1/artifacts/file-generated-test-1/content",
      expect.objectContaining({ headers: expect.objectContaining({ Accept: "application/json" }) }),
    );
  });
});
