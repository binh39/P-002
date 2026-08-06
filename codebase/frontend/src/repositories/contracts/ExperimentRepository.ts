import type { BaselineRun, CreateExperimentInput, Experiment } from "@/domain/experiments";

export interface ExperimentRepository {
  list(signal?: AbortSignal): Promise<Experiment[]>;
  create(input: CreateExperimentInput): Promise<Experiment>;
  get(experimentId: string, signal?: AbortSignal): Promise<Experiment>;
  requestBaseline(experimentId: string): Promise<BaselineRun>;
  getBaselineRun(runId: string, signal?: AbortSignal): Promise<BaselineRun>;
  downloadBaselineArtifact(runId: string, artifactName: string): Promise<Blob>;
}
