import type { PromptRole, TestGenerationRun, TestGenerationRunList } from "@/domain/experiments";

export interface CreateTestGenerationInput {
  promptRole: PromptRole;
  idempotencyKey: string;
}

export interface TestGenerationRepository {
  list(signal?: AbortSignal): Promise<TestGenerationRunList>;
  create(
    experimentId: string,
    input: CreateTestGenerationInput,
    signal?: AbortSignal,
  ): Promise<TestGenerationRun>;
}
