export type ExperimentStatus =
  | "draft"
  | "baseline_queued"
  | "baseline_running"
  | "baseline_succeeded"
  | "optimization_queued"
  | "optimizing"
  | "candidate_evaluating"
  | "paused"
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
  baselinePrompt: PromptBundle | null;
  optimizationEligible: boolean;
  status: ExperimentStatus;
  baselineRunId: string | null;
  optimizationRunId: string | null;
  comparisonRunId: string | null;
  promptVersionId: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface PromptBundle {
  initial: string;
  error: string;
  missing_coverage?: string;
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
  baselinePrompt: PromptBundle | null;
}

export interface OptimizationRun {
  id: string;
  experimentId: string;
  status: ExperimentStatus;
  parentPromptDigest: string;
  candidatePrompt: PromptBundle | null;
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
  pauseReason: string | null;
  pausedAt: string | null;
  resumeCount: number;
  maxConcurrency: number | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface EvolutionIteration {
  iteration: number;
  strategy: string;
  parentProgram: string | null;
  parentValidationScore: number | null;
  component: string | null;
  proposedPrompt: string | null;
  parentMinibatchSum: number | null;
  candidateMinibatchSum: number | null;
  decision: string;
  outcomeDetail?: string | null;
  fullValidation: boolean;
  bestStatement: number | null;
  bestBranch: number | null;
  bestScore: number | null;
  bestCandidateChanged: boolean;
}

export interface EvolutionMetricPoint {
  iteration: number;
  statement: number | null;
  branch: number | null;
  score: number | null;
}

export interface OptimizationEvolution {
  available: boolean;
  source: string;
  message: string;
  iterations: EvolutionIteration[];
  metrics: EvolutionMetricPoint[];
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

export type PromptRole = "baseline" | "optimized";
export type PromptSnapshotOrigin = "initial_baseline" | "optimized_candidate" | "baseline_retained";

export interface PromptCoverageMetrics {
  score: number | null;
  statementCoverage: number | null;
  branchCoverage: number | null;
  passRate: number | null;
}

export interface PromptSnapshot {
  id: string;
  experimentId: string;
  role: PromptRole;
  origin: PromptSnapshotOrigin;
  promptDigest: string;
  prompt: PromptBundle;
  sourceSnapshotDigest: string;
  datasetDigest: string;
  splitSeed: number;
  runnerProtocolVersion: number;
  coverupModel: string;
  optimizeModel: string;
  metrics: PromptCoverageMetrics;
  estimatedCostUsd: number | null;
  createdAt: string;
}

export interface PromptRegistryEntry {
  experimentId: string;
  experimentName: string;
  projectIds: string[];
  projectNames: string[];
  status: ExperimentStatus;
  baseline: PromptSnapshot;
  optimized: PromptSnapshot | null;
  baselineMetrics: PromptCoverageMetrics;
  optimizedMetrics: PromptCoverageMetrics;
  absoluteGain: number | null;
  createdAt: string;
  updatedAt: string;
}

export interface PromptRegistryList {
  items: PromptRegistryEntry[];
  total: number;
  offset: number;
  limit: number;
}

export type TestGenerationStatus =
  | "queued"
  | "preparing"
  | "generating"
  | "running_tests"
  | "completed"
  | "partial"
  | "failed"
  | "cancelled"
  | "timed_out";

export interface TestGenerationMetrics {
  testFileCount: number;
  testCount: number;
  passed: number | null;
  failed: number | null;
  skipped: number | null;
  projectStatementCoverage: number | null;
  projectBranchCoverage: number | null;
  targetStatementCoverage: number | null;
  targetBranchCoverage: number | null;
  targetScore: number | null;
  targetCount: number;
  completedTargetCount: number;
  failedTargetCount: number;
}

export interface TestGenerationRun {
  id: string;
  experimentId: string;
  name: string;
  promptSnapshotId: string;
  promptDigest: string;
  promptRole: PromptRole;
  status: TestGenerationStatus;
  projectIds: string[];
  samplingMethod: "random" | "most_branches" | "most_statements" | "manual";
  runtimeEnvironmentId: string | null;
  sourceSnapshotDigest: string;
  datasetDigest: string;
  scope: "project" | "modules" | "functions";
  sourceFiles: string[];
  functionIds: string[];
  targetIds: string[];
  model: string;
  randomSeed: number;
  repeatTests: number;
  maxAttempts: number;
  maxConcurrency: number;
  rateLimit: number | null;
  costCeilingUsd: number | null;
  runnerProtocolVersion: number;
  metrics: TestGenerationMetrics;
  estimatedCostUsd: number;
  tokenUsage: Record<string, number>;
  artifactObjects: Record<string, string>;
  errorMessage: string | null;
  createdAt: string;
  startedAt: string | null;
  finishedAt: string | null;
}

export interface TestGenerationRunList {
  items: TestGenerationRun[];
  total: number;
  offset: number;
  limit: number;
}

export const optimizationRunIsActive = (status: ExperimentStatus) =>
  status === "optimization_queued" || status === "optimizing" || status === "candidate_evaluating";

export const comparisonRunIsActive = (status: ExperimentStatus) =>
  status === "comparison_queued" || status === "comparing";
