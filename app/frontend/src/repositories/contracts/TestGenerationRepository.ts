import type { PromptRole, TestGenerationRun, TestGenerationRunList } from "@/domain/experiments";
import type { SamplingMethod } from "@/domain/experimentConfiguration";

export interface CreateTestGenerationInput {
  promptRole: PromptRole;
  name?: string;
  projectIds?: string[];
  samplingMethod?: SamplingMethod;
  functionCount?: number | null;
  functionIds?: string[];
  model?: string;
  randomSeed?: number;
  idempotencyKey: string;
}

export interface TestGenerationRepository {
  list(signal?: AbortSignal): Promise<TestGenerationRunList>;
  get(runId: string, signal?: AbortSignal): Promise<TestGenerationRun>;
  delete(runId: string): Promise<void>;
  getManifest(runId: string, signal?: AbortSignal): Promise<Record<string, unknown>>;
  getTextArtifact(
    runId: string,
    artifactName: string,
    signal?: AbortSignal,
  ): Promise<{ artifactName: string; content: string }>;
  downloadArtifact(runId: string, artifactName: string): Promise<Blob>;
  create(
    experimentId: string,
    input: CreateTestGenerationInput,
    signal?: AbortSignal,
  ): Promise<TestGenerationRun>;
}
