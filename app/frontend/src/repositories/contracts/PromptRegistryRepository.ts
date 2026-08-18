import type { PromptRegistryEntry, PromptRegistryList } from "@/domain/experiments";

export interface PromptRegistryRepository {
  list(signal?: AbortSignal): Promise<PromptRegistryList>;
  get(experimentId: string, signal?: AbortSignal): Promise<PromptRegistryEntry>;
}
