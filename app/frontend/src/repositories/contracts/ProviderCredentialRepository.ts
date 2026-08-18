import type { AIProvider, ProviderCredential } from "@/domain/providerCredentials";

export interface ProviderCredentialRepository {
  list(signal?: AbortSignal): Promise<ProviderCredential[]>;
  save(provider: AIProvider, apiKey: string): Promise<ProviderCredential>;
  remove(provider: AIProvider): Promise<void>;
}
