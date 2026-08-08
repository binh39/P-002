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
  projectIds: string[];
  name: string;
  targetFunctionIds: string[];
  datasetSplits: Record<string, string[]>;
  samplingMethod: import("@/domain/experimentConfiguration").SamplingMethod;
  maxTargets: number | null;
  splitSeed: number;
  splitPercentages: import("@/domain/experimentConfiguration").DatasetPercentages;
  settings: import("@/domain/experimentConfiguration").CloudExperimentSettings;
  optimizationEligible: boolean;
  status: ExperimentStatus;
  baselineRunId: string | null;
  optimizationRunId: string | null;
  comparisonRunId: string | null;
  promptVersionId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface CreateExperimentInput {
  projectIds: string[];
  name: string;
  samplingMethod: import("@/domain/experimentConfiguration").SamplingMethod;
  maxTargets: number | null;
  randomSeed: number;
  splitPercentages: import("@/domain/experimentConfiguration").DatasetPercentages;
  manualSplits: Record<string, string[]> | null;
  settings: import("@/domain/experimentConfiguration").CloudExperimentSettings;
}

export interface OptimizationRun {
  id: string;
  experimentId: string;
  status: ExperimentStatus;
  parentPromptDigest: string;
  candidatePrompt: Record<string, string> | null;
  candidatePromptDigest: string | null;
  baselineValidationScore: number | null;
  candidateValidationScore: number | null;
  candidateCount: number;
  metricCalls: number;
  finalComparison: {
    baselineMetrics: ComparisonMetrics;
    candidateMetrics: ComparisonMetrics;
    absoluteGain: number | null;
    promoted: boolean;
    skipped: boolean;
    reason: string | null;
  } | null;
  artifacts: string[];
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface ComparisonMetrics {
  score: number | null;
  statementCoverage: number | null;
  branchCoverage: number | null;
  passRate: number | null;
  latencySeconds: number | null;
  sampleCount: number | null;
  timeoutCount: number | null;
  flakyTargets: string[];
}

export interface ComparisonRun {
  id: string;
  experimentId: string;
  optimizationRunId: string;
  status: ExperimentStatus;
  baselinePromptDigest: string;
  candidatePromptDigest: string;
  testTargetIds: string[];
  replicateCount: number;
  baselineMetrics: ComparisonMetrics;
  candidateMetrics: ComparisonMetrics;
  absoluteGain: number | null;
  relativeGain: number | null;
  promotionEligible: boolean;
  decisionReason: string;
  artifacts: string[];
  promptVersionId: string | null;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export type PromptVersionStatus = "in_review" | "approved" | "rejected";

export interface PromptVersion {
  id: string;
  experimentId: string;
  comparisonRunId: string;
  parentPromptDigest: string;
  promptDigest: string;
  prompt: Record<string, string>;
  status: PromptVersionStatus;
  reviewerId: string | null;
  reviewComment: string;
  reviewedAt: string | null;
  createdAt: string;
}

export interface PromptVersionList {
  items: PromptVersion[];
  total: number;
  offset: number;
  limit: number;
}

export const optimizationRunIsActive = (status: ExperimentStatus) =>
  status === "optimization_queued" || status === "optimizing" || status === "candidate_evaluating";

export const comparisonRunIsActive = (status: ExperimentStatus) =>
  status === "comparison_queued" || status === "comparing";
