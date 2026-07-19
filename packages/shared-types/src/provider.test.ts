import { describe, expect, it } from "vitest";

import {
  PROMPT_VERSIONS,
  PROVIDER_IDS,
  type ExecuteRunRequest,
  type ProviderCollection,
} from "./provider.js";

describe("provider contracts", () => {
  it("keeps the initial provider and prompt choices closed and explicit", () => {
    expect(PROVIDER_IDS).toEqual(["mensura.builtin", "openai"]);
    expect(PROMPT_VERSIONS).toEqual(["review.v1"]);

    const request: ExecuteRunRequest = { providerId: "mensura.builtin" };
    expect(request.providerId).toBe("mensura.builtin");
  });

  it("represents redacted provider configuration without a secret field", () => {
    const providers: ProviderCollection = {
      total: 2,
      items: [
        {
          id: "mensura.builtin",
          name: "Deterministic review",
          kind: "deterministic",
          configured: true,
          model: null,
          promptVersion: "review.v1",
        },
        {
          id: "openai",
          name: "OpenAI",
          kind: "real",
          configured: false,
          model: null,
          promptVersion: "review.v1",
        },
      ],
    };

    expect(providers.items[1]).not.toHaveProperty("apiKey");
  });
});
