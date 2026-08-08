import type {
  ComparisonRun,
  CreateExperimentInput,
  Experiment,
  OptimizationRun,
} from "@/domain/experiments";

export interface ExperimentRepository {
  list(signal?: AbortSignal): Promise<Experiment[]>;
  create(input: CreateExperimentInput): Promise<Experiment>;
  delete(experimentId: string): Promise<void>;
  get(experimentId: string, signal?: AbortSignal): Promise<Experiment>;
  requestOptimization(experimentId: string): Promise<OptimizationRun>;
  getOptimizationRun(runId: string, signal?: AbortSignal): Promise<OptimizationRun>;
  downloadOptimizationArtifact(runId: string, artifactName: string): Promise<Blob>;
  requestComparison(experimentId: string): Promise<ComparisonRun>;
  getComparisonRun(runId: string, signal?: AbortSignal): Promise<ComparisonRun>;
  downloadComparisonArtifact(runId: string, artifactName: string): Promise<Blob>;
}
