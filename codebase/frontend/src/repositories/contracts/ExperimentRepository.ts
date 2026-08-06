import type {
  BaselineRun,
  CreateExperimentInput,
  Experiment,
  OptimizationRun,
} from "@/domain/experiments";

export interface ExperimentRepository {
  list(signal?: AbortSignal): Promise<Experiment[]>;
  create(input: CreateExperimentInput): Promise<Experiment>;
  get(experimentId: string, signal?: AbortSignal): Promise<Experiment>;
  requestBaseline(experimentId: string): Promise<BaselineRun>;
  getBaselineRun(runId: string, signal?: AbortSignal): Promise<BaselineRun>;
  downloadBaselineArtifact(runId: string, artifactName: string): Promise<Blob>;
  requestOptimization(experimentId: string): Promise<OptimizationRun>;
  getOptimizationRun(runId: string, signal?: AbortSignal): Promise<OptimizationRun>;
  downloadOptimizationArtifact(runId: string, artifactName: string): Promise<Blob>;
}
