import type {
  ComparisonRun,
  CreateExperimentInput,
  Experiment,
  OptimizationEvolution,
  OptimizationRun,
} from "@/domain/experiments";

export interface ExperimentRepository {
  list(signal?: AbortSignal): Promise<Experiment[]>;
  create(input: CreateExperimentInput): Promise<Experiment>;
  delete(experimentId: string): Promise<void>;
  get(experimentId: string, signal?: AbortSignal): Promise<Experiment>;
  requestOptimization(experimentId: string): Promise<OptimizationRun>;
  getOptimizationRun(runId: string, signal?: AbortSignal): Promise<OptimizationRun>;
  cancelOptimization(runId: string): Promise<OptimizationRun>;
  resumeOptimization(runId: string, maxConcurrency: number): Promise<OptimizationRun>;
  getOptimizationEvolution(runId: string, signal?: AbortSignal): Promise<OptimizationEvolution>;
  downloadOptimizationArtifact(runId: string, artifactName: string): Promise<Blob>;
  requestComparison(experimentId: string): Promise<ComparisonRun>;
  getComparisonRun(runId: string, signal?: AbortSignal): Promise<ComparisonRun>;
  downloadComparisonArtifact(runId: string, artifactName: string): Promise<Blob>;
}
