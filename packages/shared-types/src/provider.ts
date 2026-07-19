export const PROVIDER_IDS = ["mensura.builtin", "openai"] as const;
export type ProviderId = (typeof PROVIDER_IDS)[number];

export const PROVIDER_KINDS = ["deterministic", "real"] as const;
export type ProviderKind = (typeof PROVIDER_KINDS)[number];

export const PROMPT_VERSIONS = ["review.v1", "review.v2"] as const;
export type PromptVersion = (typeof PROMPT_VERSIONS)[number];

export interface ProviderDescriptor {
  id: ProviderId;
  name: string;
  kind: ProviderKind;
  configured: boolean;
  model: string | null;
  promptVersion: PromptVersion;
}

export interface ProviderCollection {
  items: readonly ProviderDescriptor[];
  total: number;
}

/** The apiKey is write-only and is never returned by Core. */
export interface ConfigureOpenAIProviderRequest {
  apiKey: string;
  model: string;
}

export interface ExecuteRunRequest {
  providerId: ProviderId;
}
