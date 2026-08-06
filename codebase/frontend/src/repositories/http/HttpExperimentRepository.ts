import { apiDownload, apiRequest } from "@/api/client";
import type {
  BaselineRun,
  CreateExperimentInput,
  Experiment,
  ExperimentStatus,
  OptimizationRun,
  TargetMetric,
} from "@/domain/experiments";
import type { ExperimentRepository } from "@/repositories/contracts/ExperimentRepository";

interface ApiExperiment {
  id: string;
  project_id: string;
  name: string;
  target_function_ids: string[];
  dataset_splits: Record<string, string[]>;
  optimization_eligible: boolean;
  status: ExperimentStatus;
  baseline_run_id: string | null;
  optimization_run_id: string | null;
  comparison_run_id: string | null;
  prompt_version_id: string | null;
  created_at: string;
  updated_at: string;
}

interface ApiExperimentList {
  items: ApiExperiment[];
  total: number;
}

interface ApiTargetMetric {
  valid?: boolean;
  score?: number;
  covered_statements?: number;
  num_statements?: number;
  covered_branches?: number;
  num_branches?: number;
  statement_coverage?: number;
  branch_coverage?: number;
}

interface ApiBaselineRun {
  id: string;
  experiment_id: string;
  status: ExperimentStatus;
  target_count: number;
  coverage_score: number | null;
  statement_coverage: number | null;
  branch_coverage: number | null;
  prompt_digest: string | null;
  artifact_objects: Record<string, string>;
  target_metrics: Record<string, ApiTargetMetric>;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

interface ApiOptimizationRun {
  id: string;
  experiment_id: string;
  status: ExperimentStatus;
  parent_prompt_digest: string;
  candidate_prompt: Record<string, string> | null;
  candidate_prompt_digest: string | null;
  baseline_validation_score: number | null;
  candidate_validation_score: number | null;
  candidate_count: number;
  metric_calls: number;
  artifact_objects: Record<string, string>;
  error_message: string | null;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}

function mapExperiment(item: ApiExperiment): Experiment {
  return {
    id: item.id,
    projectId: item.project_id,
    name: item.name,
    targetFunctionIds: item.target_function_ids,
    datasetSplits: item.dataset_splits,
    optimizationEligible: item.optimization_eligible,
    status: item.status,
    baselineRunId: item.baseline_run_id,
    optimizationRunId: item.optimization_run_id,
    comparisonRunId: item.comparison_run_id,
    promptVersionId: item.prompt_version_id,
    createdAt: item.created_at,
    updatedAt: item.updated_at,
  };
}

function mapOptimizationRun(item: ApiOptimizationRun): OptimizationRun {
  return {
    id: item.id,
    experimentId: item.experiment_id,
    status: item.status,
    parentPromptDigest: item.parent_prompt_digest,
    candidatePrompt: item.candidate_prompt,
    candidatePromptDigest: item.candidate_prompt_digest,
    baselineValidationScore: item.baseline_validation_score,
    candidateValidationScore: item.candidate_validation_score,
    candidateCount: item.candidate_count,
    metricCalls: item.metric_calls,
    artifacts: Object.keys(item.artifact_objects).sort(),
    errorMessage: item.error_message,
    createdAt: item.created_at,
    startedAt: item.started_at,
    finishedAt: item.finished_at,
  };
}

function mapTargetMetric(item: ApiTargetMetric): TargetMetric {
  return {
    valid: item.valid,
    score: item.score,
    coveredStatements: item.covered_statements,
    numStatements: item.num_statements,
    coveredBranches: item.covered_branches,
    numBranches: item.num_branches,
    statementCoverage: item.statement_coverage,
    branchCoverage: item.branch_coverage,
  };
}

function mapBaselineRun(item: ApiBaselineRun): BaselineRun {
  return {
    id: item.id,
    experimentId: item.experiment_id,
    status: item.status,
    targetCount: item.target_count,
    coverageScore: item.coverage_score,
    statementCoverage: item.statement_coverage,
    branchCoverage: item.branch_coverage,
    promptDigest: item.prompt_digest,
    artifacts: Object.keys(item.artifact_objects).sort(),
    targetMetrics: Object.fromEntries(
      Object.entries(item.target_metrics).map(([name, metric]) => [name, mapTargetMetric(metric)]),
    ),
    errorMessage: item.error_message,
    createdAt: item.created_at,
    startedAt: item.started_at,
    finishedAt: item.finished_at,
  };
}

export class HttpExperimentRepository implements ExperimentRepository {
  async list(signal?: AbortSignal) {
    const response = await apiRequest<ApiExperimentList>("/experiments", { signal });
    return response.items.map(mapExperiment);
  }

  async create(input: CreateExperimentInput) {
    return mapExperiment(
      await apiRequest<ApiExperiment>("/experiments", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          project_id: input.projectId,
          name: input.name,
          target_function_ids: input.targetFunctionIds,
        }),
      }),
    );
  }

  async get(experimentId: string, signal?: AbortSignal) {
    return mapExperiment(
      await apiRequest<ApiExperiment>(`/experiments/${experimentId}`, { signal }),
    );
  }

  async requestBaseline(experimentId: string) {
    return mapBaselineRun(
      await apiRequest<ApiBaselineRun>(`/experiments/${experimentId}/runs`, { method: "POST" }),
    );
  }

  async getBaselineRun(runId: string, signal?: AbortSignal) {
    return mapBaselineRun(
      await apiRequest<ApiBaselineRun>(`/experiments/runs/${runId}`, { signal }),
    );
  }

  downloadBaselineArtifact(runId: string, artifactName: string) {
    return apiDownload(`/experiments/runs/${runId}/artifacts/${encodeURIComponent(artifactName)}`);
  }

  async requestOptimization(experimentId: string) {
    return mapOptimizationRun(
      await apiRequest<ApiOptimizationRun>(`/experiments/${experimentId}/optimize`, {
        method: "POST",
      }),
    );
  }

  async getOptimizationRun(runId: string, signal?: AbortSignal) {
    return mapOptimizationRun(
      await apiRequest<ApiOptimizationRun>(`/experiments/optimization-runs/${runId}`, { signal }),
    );
  }

  downloadOptimizationArtifact(runId: string, artifactName: string) {
    return apiDownload(
      `/experiments/optimization-runs/${runId}/artifacts/${encodeURIComponent(artifactName)}`,
    );
  }
}
