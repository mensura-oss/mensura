import type { ProviderCollection, ProviderDescriptor } from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { ProviderSettingsPanel } from "./ProviderSettingsPanel";

describe("ProviderSettingsPanel", () => {
  it("shows deterministic fallback and redacted OpenAI configuration state", async () => {
    const user = userEvent.setup();
    const client = createTestClient({
      listProviders: () => Promise.resolve(configuredProviders),
    });

    renderWithAppProviders(<ProviderSettingsPanel />, client);

    expect(screen.getByText("Deterministic review")).toBeVisible();
    expect(await screen.findByText("configured")).toBeVisible();
    expect(screen.getByText(/gpt-5-mini · review.v2/)).toBeVisible();
    expect(screen.getByLabelText("OpenAI API key")).toHaveValue("");
    expect(screen.queryByText("sk-secret")).toBeNull();

    await user.clear(screen.getByLabelText("OpenAI model"));
    await user.type(screen.getByLabelText("OpenAI model"), "gpt-5-nano");
    expect(screen.getByLabelText("OpenAI model")).toHaveValue("gpt-5-nano");
  });

  it("validates locally, preserves fields on failure, and clears the key on success", async () => {
    const user = userEvent.setup();
    let shouldFail = true;
    const configureOpenAIProvider = vi.fn(() => {
      if (shouldFail) {
        return Promise.reject(
          new CoreApiError({
            type: "urn:mensura:problem:provider-configuration-unavailable",
            title: "Provider configuration unavailable",
            status: 503,
            detail: "The OS credential backend is unavailable.",
          }),
        );
      }
      return Promise.resolve(configuredOpenAI);
    });
    const client = createTestClient({
      listProviders: () => Promise.resolve(unconfiguredProviders),
      configureOpenAIProvider,
    });

    renderWithAppProviders(<ProviderSettingsPanel />, client);
    await screen.findByText("not configured");
    await user.click(screen.getByRole("button", { name: "Save OpenAI config" }));

    expect(screen.getByText("Enter a valid provider model ID.")).toBeVisible();
    expect(screen.getByText(/Enter a complete API key/)).toBeVisible();
    expect(configureOpenAIProvider).not.toHaveBeenCalled();

    await user.type(screen.getByLabelText("OpenAI model"), "gpt-5-mini");
    await user.type(
      screen.getByLabelText("OpenAI API key"),
      "sk-local-write-only-secret",
    );
    await user.click(screen.getByRole("button", { name: "Save OpenAI config" }));

    expect(await screen.findByText("Provider configuration unavailable")).toBeVisible();
    expect(screen.getByLabelText("OpenAI model")).toHaveValue("gpt-5-mini");
    expect(screen.getByLabelText("OpenAI API key")).toHaveValue(
      "sk-local-write-only-secret",
    );

    shouldFail = false;
    await user.click(screen.getByRole("button", { name: "Save OpenAI config" }));

    expect(
      await screen.findByText(/OpenAI configuration saved locally/),
    ).toBeVisible();
    expect(screen.getByLabelText("OpenAI API key")).toHaveValue("");
    expect(configureOpenAIProvider).toHaveBeenLastCalledWith({
      apiKey: "sk-local-write-only-secret",
      model: "gpt-5-mini",
    });
  });
});

const deterministic: ProviderDescriptor = {
  id: "mensura.builtin",
  name: "Deterministic review",
  kind: "deterministic",
  configured: true,
  model: null,
  promptVersion: "review.v2",
};

const unconfiguredOpenAI: ProviderDescriptor = {
  id: "openai",
  name: "OpenAI",
  kind: "real",
  configured: false,
  model: null,
  promptVersion: "review.v2",
};

const configuredOpenAI: ProviderDescriptor = {
  ...unconfiguredOpenAI,
  configured: true,
  model: "gpt-5-mini",
};

const unconfiguredProviders: ProviderCollection = {
  total: 2,
  items: [deterministic, unconfiguredOpenAI],
};

const configuredProviders: ProviderCollection = {
  total: 2,
  items: [deterministic, configuredOpenAI],
};
