export type ExperimentStatus =
  | "draft"
  | "baseline_queued"
  | "baseline_running"
  | "baseline_succeeded"
  | "optimization_queued"
  | "optimizing"
  | "candidate_evaluating"
  | "optimization_succeeded"
  | "comparison_queued"
  | "comparing"
  | "comparison_succeeded"
  | "in_review"
  | "approved"
  | "rejected"
  | "timed_out"
  | "cancelled"
  | "failed";

export interface Experiment {
  id: string;
  projectId: string;
  name: string;
  targetFunctionIds: string[];
  datasetSplits: Record<string, string[]>;
  optimizationEligible: boolean;
  status: ExperimentStatus;
  baselineRunId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateExperimentInput {
  projectId: string;
  name: string;
  targetFunctionIds: string[];
}

export interface TargetMetric {
  valid?: boolean;
  score?: number;
  coveredStatements?: number;
  numStatements?: number;
  coveredBranches?: number;
  numBranches?: number;
  statementCoverage?: number;
  branchCoverage?: number;
}

export interface BaselineRun {
  id: string;
  experimentId: string;
  status: ExperimentStatus;
  targetCount: number;
  coverageScore: number | null;
  statementCoverage: number | null;
  branchCoverage: number | null;
  promptDigest: string | null;
  artifacts: string[];
  targetMetrics: Record<string, TargetMetric>;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export const baselineRunIsActive = (status: ExperimentStatus) =>
  status === "baseline_queued" || status === "baseline_running";

export const baselineRunIsFinished = (status: ExperimentStatus) =>
  status === "baseline_succeeded" ||
  status === "failed" ||
  status === "timed_out" ||
  status === "cancelled";
