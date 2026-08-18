import { apiRequest } from "@/api/client";
import type {
  TestGenerationMetrics,
  TestGenerationRun,
  TestGenerationRunList,
} from "@/domain/experiments";
import type {
  CreateTestGenerationInput,
  TestGenerationRepository,
} from "@/repositories/contracts/TestGenerationRepository";

interface ApiTestGenerationMetrics {
  test_file_count: number;
  test_count: number;
  passed: number | null;
  failed: number | null;
  skipped: number | null;
  project_statement_coverage: number | null;
  project_branch_coverage: number | null;
  target_statement_coverage: number | null;
  target_branch_coverage: number | null;
  target_score: number | null;
  target_count: number;
  completed_target_count: number;
  failed_target_count: number;
}

interface ApiTestGenerationRun {
  id: string;
  experiment_id: string;
  prompt_snapshot_id: string;
  prompt_digest: string;
  prompt_role: TestGenerationRun["promptRole"];
  status: TestGenerationRun["status"];
  project_ids: string[];
  scope: TestGenerationRun["scope"];
  model: string;
  metrics: ApiTestGenerationMetrics;
  estimated_cost_usd: number;
  error_message: string | null;
  created_at: string;
}

interface ApiTestGenerationRunList {
  items: ApiTestGenerationRun[];
  total: number;
  offset: number;
  limit: number;
}

function mapMetrics(metrics: ApiTestGenerationMetrics): TestGenerationMetrics {
  return {
    testFileCount: metrics.test_file_count,
    testCount: metrics.test_count,
    passed: metrics.passed,
    failed: metrics.failed,
    skipped: metrics.skipped,
    projectStatementCoverage: metrics.project_statement_coverage,
    projectBranchCoverage: metrics.project_branch_coverage,
    targetStatementCoverage: metrics.target_statement_coverage,
    targetBranchCoverage: metrics.target_branch_coverage,
    targetScore: metrics.target_score,
    targetCount: metrics.target_count,
    completedTargetCount: metrics.completed_target_count,
    failedTargetCount: metrics.failed_target_count,
  };
}

function mapRun(run: ApiTestGenerationRun): TestGenerationRun {
  return {
    id: run.id,
    experimentId: run.experiment_id,
    promptSnapshotId: run.prompt_snapshot_id,
    promptDigest: run.prompt_digest,
    promptRole: run.prompt_role,
    status: run.status,
    projectIds: run.project_ids,
    scope: run.scope,
    model: run.model,
    metrics: mapMetrics(run.metrics),
    estimatedCostUsd: run.estimated_cost_usd,
    errorMessage: run.error_message,
    createdAt: run.created_at,
  };
}

export class HttpTestGenerationRepository implements TestGenerationRepository {
  async list(signal?: AbortSignal): Promise<TestGenerationRunList> {
    const response = await apiRequest<ApiTestGenerationRunList>("/test-generation-runs?limit=100", {
      signal,
    });
    return { ...response, items: response.items.map(mapRun) };
  }

  async create(
    experimentId: string,
    input: CreateTestGenerationInput,
    signal?: AbortSignal,
  ): Promise<TestGenerationRun> {
    return mapRun(
      await apiRequest<ApiTestGenerationRun>(`/prompt-registry/${experimentId}/test-generation`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          prompt_role: input.promptRole,
          scope: "project",
          idempotency_key: input.idempotencyKey,
        }),
        signal,
      }),
    );
  }
}
