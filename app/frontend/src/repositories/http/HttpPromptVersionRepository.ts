import { apiRequest } from "@/api/client";
import type {
  ComparisonMetrics,
  ComparisonRun,
  PromptVersion,
  PromptVersionList,
  ReviewDetail,
} from "@/domain/experiments";
import type { PromptVersionRepository } from "@/repositories/contracts/PromptVersionRepository";

interface ApiPromptVersion {
  id: string;
  experiment_id: string;
  comparison_run_id: string;
  parent_prompt_digest: string;
  prompt_digest: string;
  prompt: Record<string, string>;
  status: "in_review" | "approved" | "rejected";
  reviewer_id: string | null;
  review_comment: string;
  reviewed_at: string | null;
  created_by: string | null;
  workspace_id: string | null;
  created_at: string;
}

interface ApiPromptVersionList {
  items: ApiPromptVersion[];
  total: number;
  offset: number;
  limit: number;
}

interface ApiComparisonRun {
  id: string;
  experiment_id: string;
  optimization_run_id: string;
  status: ComparisonRun["status"];
  baseline_prompt_digest: string;
  candidate_prompt_digest: string;
  test_target_ids: string[];
  replicate_count: number;
  baseline_metrics: Record<string, unknown>;
  candidate_metrics: Record<string, unknown>;
  absolute_gain: number | null;
  relative_gain: number | null;
  promotion_eligible: boolean;
  decision_reason: string;
  artifact_objects: Record<string, string>;
  prompt_version_id: string | null;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

function mapMetrics(value: Record<string, unknown>): ComparisonMetrics {
  return {
    score: typeof value.score === "number" ? value.score : null,
    statementCoverage:
      typeof value.statement_coverage === "number" ? value.statement_coverage : null,
    branchCoverage: typeof value.branch_coverage === "number" ? value.branch_coverage : null,
    passRate: typeof value.pass_rate === "number" ? value.pass_rate : null,
    latencySeconds: typeof value.latency_seconds === "number" ? value.latency_seconds : null,
    sampleCount: typeof value.sample_count === "number" ? value.sample_count : null,
    timeoutCount: typeof value.timeout_count === "number" ? value.timeout_count : null,
    flakyTargets: Array.isArray(value.flaky_targets) ? value.flaky_targets.map(String) : [],
  };
}

function mapComparison(item: ApiComparisonRun): ComparisonRun {
  return {
    id: item.id,
    experimentId: item.experiment_id,
    optimizationRunId: item.optimization_run_id,
    status: item.status,
    baselinePromptDigest: item.baseline_prompt_digest,
    candidatePromptDigest: item.candidate_prompt_digest,
    testTargetIds: item.test_target_ids,
    replicateCount: item.replicate_count,
    baselineMetrics: mapMetrics(item.baseline_metrics),
    candidateMetrics: mapMetrics(item.candidate_metrics),
    absoluteGain: item.absolute_gain,
    relativeGain: item.relative_gain,
    promotionEligible: item.promotion_eligible,
    decisionReason: item.decision_reason,
    artifacts: Object.keys(item.artifact_objects),
    promptVersionId: item.prompt_version_id,
    errorMessage: item.error_message,
    createdAt: item.created_at,
    startedAt: item.started_at,
    finishedAt: item.finished_at,
  };
}

function mapPromptVersion(item: ApiPromptVersion): PromptVersion {
  return {
    id: item.id,
    experimentId: item.experiment_id,
    comparisonRunId: item.comparison_run_id,
    parentPromptDigest: item.parent_prompt_digest,
    promptDigest: item.prompt_digest,
    prompt: item.prompt,
    status: item.status,
    reviewerId: item.reviewer_id,
    reviewComment: item.review_comment,
    reviewedAt: item.reviewed_at,
    createdBy: item.created_by,
    workspaceId: item.workspace_id,
    createdAt: item.created_at,
  };
}

function mapPromptBundle(item: Record<string, string>) {
  return {
    initial: item.initial ?? "",
    error: item.error ?? "",
    ...(item.missing_coverage ? { missing_coverage: item.missing_coverage } : {}),
  };
}

export class HttpPromptVersionRepository implements PromptVersionRepository {
  async list(
    status?: "in_review" | "approved" | "rejected",
    signal?: AbortSignal,
  ): Promise<PromptVersionList> {
    const params = new URLSearchParams({ limit: "50" });
    if (status) params.set("status", status);
    const response = await apiRequest<ApiPromptVersionList>(`/reviews?${params}`, {
      signal,
    });
    return { ...response, items: response.items.map(mapPromptVersion) };
  }

  async get(versionId: string, signal?: AbortSignal) {
    return mapPromptVersion(
      await apiRequest<ApiPromptVersion>(`/prompt-versions/${versionId}`, { signal }),
    );
  }

  async getReview(versionId: string, signal?: AbortSignal): Promise<ReviewDetail> {
    const response = await apiRequest<{
      version: ApiPromptVersion;
      experiment_name: string;
      creator_id: string;
      baseline_prompt: Record<string, string>;
      candidate_prompt: Record<string, string>;
      comparison: ApiComparisonRun;
      artifact_names: string[];
    }>(`/reviews/${versionId}`, { signal });
    return {
      version: mapPromptVersion(response.version),
      experimentName: response.experiment_name,
      creatorId: response.creator_id,
      baselinePrompt: mapPromptBundle(response.baseline_prompt),
      candidatePrompt: mapPromptBundle(response.candidate_prompt),
      comparison: mapComparison(response.comparison),
      artifactNames: response.artifact_names,
    };
  }

  async review(versionId: string, decision: "approve" | "reject", comment: string) {
    return mapPromptVersion(
      await apiRequest<ApiPromptVersion>(`/prompt-versions/${versionId}/${decision}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment }),
      }),
    );
  }
}
