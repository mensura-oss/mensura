import type {
  VaultFileInventoryItem,
  VaultFilePreview,
} from "@mensura/shared-types";
import { screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { CoreApiError } from "../../api/coreClient";
import { createTestClient, renderWithAppProviders } from "../../test/render";
import { WorkspaceEditor } from "./WorkspaceEditor";

// The real viewer pulls in monaco-editor + web workers, which jsdom cannot run.
// Stub it with a plain <pre> that surfaces the props we care about.
vi.mock("./MonacoCodeViewer", async () => {
  const { createElement } = await import("react");
  return {
    default: (props: {
      value: string;
      language: string;
      highlight?: { startLine: number; endLine: number } | null;
    }) =>
      createElement(
        "pre",
        {
          "data-testid": "monaco",
          "data-language": props.language,
          "data-highlight": props.highlight
            ? `${props.highlight.startLine}-${props.highlight.endLine}`
            : "",
        },
        props.value,
      ),
  };
});

const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const inventoryId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";

const textFile: VaultFileInventoryItem = {
  path: "src/app.ts",
  name: "app.ts",
  extension: ".ts",
  language: "TypeScript",
  kind: "text",
  sizeBytes: 42,
};

function preview(overrides: Partial<VaultFilePreview> = {}): VaultFilePreview {
  return {
    inventoryId,
    workspaceId,
    file: textFile,
    encoding: "utf-8",
    text: "const answer = 42;\n",
    previewBytes: 19,
    totalBytes: 19,
    truncated: false,
    ...overrides,
  };
}

describe("WorkspaceEditor", () => {
  it("guides the user when nothing is open", () => {
    const client = createTestClient();
    renderWithAppProviders(
      <WorkspaceEditor workspaceId={workspaceId} path={null} file={null} />,
      client,
    );

    expect(
      screen.getByText("Select a file from the repository tree to view it here."),
    ).toBeVisible();
  });

  it("renders file contents with an inferred language", async () => {
    const getVaultFilePreview = vi.fn(() => Promise.resolve(preview()));
    const client = createTestClient({ getVaultFilePreview });

    renderWithAppProviders(
      <WorkspaceEditor
        workspaceId={workspaceId}
        path="src/app.ts"
        file={textFile}
      />,
      client,
    );

    const monaco = await screen.findByTestId("monaco");
    expect(monaco).toHaveTextContent("const answer = 42;");
    expect(monaco).toHaveAttribute("data-language", "typescript");
    expect(screen.getByText("Read-only")).toBeVisible();
    expect(getVaultFilePreview).toHaveBeenCalledWith(workspaceId, "src/app.ts");
  });

  it("forwards a Vault hit's line range to the viewer", async () => {
    const getVaultFilePreview = vi.fn(() => Promise.resolve(preview()));
    const client = createTestClient({ getVaultFilePreview });

    renderWithAppProviders(
      <WorkspaceEditor
        workspaceId={workspaceId}
        path="src/app.ts"
        file={textFile}
        highlight={{ startLine: 1, endLine: 1 }}
      />,
      client,
    );

    const monaco = await screen.findByTestId("monaco");
    expect(monaco).toHaveAttribute("data-highlight", "1-1");
  });

  it("notes when the preview is truncated", async () => {
    const getVaultFilePreview = vi.fn(() =>
      Promise.resolve(preview({ previewBytes: 16, totalBytes: 4096, truncated: true })),
    );
    const client = createTestClient({ getVaultFilePreview });

    renderWithAppProviders(
      <WorkspaceEditor
        workspaceId={workspaceId}
        path="src/app.ts"
        file={textFile}
      />,
      client,
    );

    expect(await screen.findByText(/truncated for preview/)).toBeVisible();
  });

  it("shows binary files as unsupported without requesting a preview", () => {
    const getVaultFilePreview = vi.fn(() => Promise.resolve(preview()));
    const binaryFile: VaultFileInventoryItem = {
      ...textFile,
      path: "assets/logo.png",
      name: "logo.png",
      extension: ".png",
      language: null,
      kind: "binary",
    };
    const client = createTestClient({ getVaultFilePreview });

    renderWithAppProviders(
      <WorkspaceEditor
        workspaceId={workspaceId}
        path="assets/logo.png"
        file={binaryFile}
      />,
      client,
    );

    expect(
      screen.getByText(
        "This is a binary file. The Workspace editor only renders text files.",
      ),
    ).toBeVisible();
    expect(getVaultFilePreview).not.toHaveBeenCalled();
  });

  it("explains an excluded / too-large file refusal", async () => {
    const getVaultFilePreview = vi.fn(() =>
      Promise.reject(
        new CoreApiError({
          type: "urn:mensura:problem:vault-file-excluded",
          title: "Vault file access excluded",
          status: 403,
        }),
      ),
    );
    const client = createTestClient({ getVaultFilePreview });

    renderWithAppProviders(
      <WorkspaceEditor
        workspaceId={workspaceId}
        path="src/huge.ts"
        file={{ ...textFile, path: "src/huge.ts", name: "huge.ts" }}
      />,
      client,
    );

    expect(
      await screen.findByText(
        "This file is too large or excluded from preview by Vault's rules.",
      ),
    ).toBeVisible();
  });
});
