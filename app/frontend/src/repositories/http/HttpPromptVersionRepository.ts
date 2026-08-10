import { apiRequest } from "@/api/client";
import type { PromptVersion, PromptVersionList } from "@/domain/experiments";
import type { PromptVersionRepository } from "@/repositories/contracts/PromptVersionRepository";

interface ApiPromptVersion {
  id: string;
  experiment_id: string;
  comparison_run_id: string;
  parent_prompt_digest: string;
  prompt_digest: string;
  prompt: Record<string, string>;
  status: "in_review" | "approved" | "rejected";
  reviewer_id: string | null;
  review_comment: string;
  reviewed_at: string | null;
  created_at: string;
}

interface ApiPromptVersionList {
  items: ApiPromptVersion[];
  total: number;
  offset: number;
  limit: number;
}

function mapPromptVersion(item: ApiPromptVersion): PromptVersion {
  return {
    id: item.id,
    experimentId: item.experiment_id,
    comparisonRunId: item.comparison_run_id,
    parentPromptDigest: item.parent_prompt_digest,
    promptDigest: item.prompt_digest,
    prompt: item.prompt,
    status: item.status,
    reviewerId: item.reviewer_id,
    reviewComment: item.review_comment,
    reviewedAt: item.reviewed_at,
    createdAt: item.created_at,
  };
}

export class HttpPromptVersionRepository implements PromptVersionRepository {
  async list(
    status?: "in_review" | "approved" | "rejected",
    signal?: AbortSignal,
  ): Promise<PromptVersionList> {
    const params = new URLSearchParams({ limit: "50" });
    if (status) params.set("status", status);
    const response = await apiRequest<ApiPromptVersionList>(`/prompt-versions?${params}`, {
      signal,
    });
    return { ...response, items: response.items.map(mapPromptVersion) };
  }

  async get(versionId: string, signal?: AbortSignal) {
    return mapPromptVersion(
      await apiRequest<ApiPromptVersion>(`/prompt-versions/${versionId}`, { signal }),
    );
  }

  async review(versionId: string, decision: "approve" | "reject", comment: string) {
    return mapPromptVersion(
      await apiRequest<ApiPromptVersion>(`/prompt-versions/${versionId}/${decision}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ comment }),
      }),
    );
  }
}
