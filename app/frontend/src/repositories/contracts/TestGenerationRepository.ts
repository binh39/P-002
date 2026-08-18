import type { PromptRole, TestGenerationRun, TestGenerationRunList } from "@/domain/experiments";

export interface CreateTestGenerationInput {
  promptRole: PromptRole;
  idempotencyKey: string;
}

export interface TestGenerationRepository {
  list(signal?: AbortSignal): Promise<TestGenerationRunList>;
  get(runId: string, signal?: AbortSignal): Promise<TestGenerationRun>;
  getManifest(runId: string, signal?: AbortSignal): Promise<Record<string, unknown>>;
  downloadArtifact(runId: string, artifactName: string): Promise<Blob>;
  create(
    experimentId: string,
    input: CreateTestGenerationInput,
    signal?: AbortSignal,
  ): Promise<TestGenerationRun>;
}
