import type { VaultFileInventoryItem } from "@mensura/shared-types";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { buildFileTree } from "./fileTree";
import { RepositoryTree } from "./RepositoryTree";

function item(
  path: string,
  overrides: Partial<VaultFileInventoryItem> = {},
): VaultFileInventoryItem {
  const name = path.slice(path.lastIndexOf("/") + 1);
  const dot = name.lastIndexOf(".");
  return {
    path,
    name,
    extension: dot > 0 ? name.slice(dot) : null,
    language: null,
    kind: "text",
    sizeBytes: 10,
    ...overrides,
  };
}

const nodes = buildFileTree([
  item("src/app.ts", { language: "TypeScript" }),
  item("README.md", { language: "Markdown" }),
]);

describe("RepositoryTree", () => {
  it("renders directories, files, and type badges expanded by default", () => {
    render(
      <RepositoryTree nodes={nodes} selectedPath={null} onSelectFile={vi.fn()} />,
    );

    expect(screen.getByRole("button", { name: "src" })).toBeVisible();
    expect(screen.getByRole("button", { name: /app\.ts/ })).toBeVisible();
    expect(screen.getByRole("button", { name: /README\.md/ })).toBeVisible();
    // Small type badges next to leaves.
    expect(screen.getByText("code")).toBeVisible();
    expect(screen.getByText("doc")).toBeVisible();
  });

  it("collapses and expands a directory", async () => {
    const user = userEvent.setup();
    render(
      <RepositoryTree nodes={nodes} selectedPath={null} onSelectFile={vi.fn()} />,
    );

    await user.click(screen.getByRole("button", { name: "src" }));
    expect(screen.queryByRole("button", { name: /app\.ts/ })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "src" }));
    expect(screen.getByRole("button", { name: /app\.ts/ })).toBeVisible();
  });

  it("reports the selected file to the caller", async () => {
    const user = userEvent.setup();
    const onSelectFile = vi.fn();
    render(
      <RepositoryTree nodes={nodes} selectedPath={null} onSelectFile={onSelectFile} />,
    );

    await user.click(screen.getByRole("button", { name: /app\.ts/ }));

    expect(onSelectFile).toHaveBeenCalledWith(
      expect.objectContaining({ path: "src/app.ts" }),
    );
  });

  it("marks the selected file as pressed", () => {
    render(
      <RepositoryTree
        nodes={nodes}
        selectedPath="src/app.ts"
        onSelectFile={vi.fn()}
      />,
    );

    expect(screen.getByRole("button", { name: /app\.ts/ })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });
});
