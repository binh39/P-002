export type AIProvider = "gemini" | "openai" | "deepseek";

export interface ProviderCredential {
  provider: AIProvider;
  configured: boolean;
  maskedKey: string | null;
}
