import { apiRequest } from "@/api/client";
import type { AIProvider, ProviderCredential } from "@/domain/providerCredentials";
import type { ProviderCredentialRepository } from "@/repositories/contracts/ProviderCredentialRepository";

interface ApiProviderCredential {
  provider: AIProvider;
  configured: boolean;
  masked_key: string | null;
}

interface ApiProviderCredentialList {
  items: ApiProviderCredential[];
}

function mapCredential(item: ApiProviderCredential): ProviderCredential {
  return {
    provider: item.provider,
    configured: item.configured,
    maskedKey: item.masked_key,
  };
}

export class HttpProviderCredentialRepository implements ProviderCredentialRepository {
  async list(signal?: AbortSignal): Promise<ProviderCredential[]> {
    const response = await apiRequest<ApiProviderCredentialList>("/provider-credentials", {
      signal,
    });
    return response.items.map(mapCredential);
  }

  async save(provider: AIProvider, apiKey: string): Promise<ProviderCredential> {
    return mapCredential(
      await apiRequest<ApiProviderCredential>(`/provider-credentials/${provider}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ api_key: apiKey }),
      }),
    );
  }

  async remove(provider: AIProvider): Promise<void> {
    await apiRequest<void>(`/provider-credentials/${provider}`, { method: "DELETE" });
  }
}
