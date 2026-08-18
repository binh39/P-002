import type { PromptRole, TestGenerationRun, TestGenerationRunList } from "@/domain/experiments";

export interface CreateTestGenerationInput {
  promptRole: PromptRole;
  idempotencyKey: string;
}

export interface TestGenerationRepository {
  list(signal?: AbortSignal): Promise<TestGenerationRunList>;
  get(runId: string, signal?: AbortSignal): Promise<TestGenerationRun>;
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
