import type { PromptRole, TestGenerationRun } from "@/domain/experiments";

export interface CreateTestGenerationInput {
  promptRole: PromptRole;
  idempotencyKey: string;
}

export interface TestGenerationRepository {
  create(
    experimentId: string,
    input: CreateTestGenerationInput,
    signal?: AbortSignal,
  ): Promise<TestGenerationRun>;
}
