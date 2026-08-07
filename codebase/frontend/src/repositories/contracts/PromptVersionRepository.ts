import type { PromptVersion, PromptVersionList } from "@/domain/experiments";

export interface PromptVersionRepository {
  list(
    status?: "in_review" | "approved" | "rejected",
    signal?: AbortSignal,
  ): Promise<PromptVersionList>;
  get(versionId: string, signal?: AbortSignal): Promise<PromptVersion>;
  review(
    versionId: string,
    decision: "approve" | "reject",
    comment: string,
  ): Promise<PromptVersion>;
}
