import type { VaultMemoryItemDetail } from "@mensura/shared-types";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { VaultFileView, type VaultFileHit } from "./VaultFileView";

const memoryItemId = "8f2b6d4a-1c3e-4f5a-9b7c-0d1e2f3a4b5c";
const workspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const indexId = "d5319f9c-9ed0-412c-a0a8-0c011d94e2c1";

// Two non-contiguous chunks (lines 1–2 and 5–6) so line 3–4 is a gap.
const detail: VaultMemoryItemDetail = {
  item: {
    id: memoryItemId,
    workspaceId,
    indexId,
    path: "src/app.ts",
    sourceType: "code",
    language: "TypeScript",
    digest: `sha256:${"a".repeat(64)}`,
    sizeBytes: 120,
    chunkCount: 2,
    indexedAt: "2026-07-22T13:00:00Z",
  },
  chunks: [
    {
      id: "chunk-a",
      memoryItemId,
      chunkIndex: 0,
      startLine: 1,
      endLine: 2,
      charCount: 18,
      digest: `sha256:${"b".repeat(64)}`,
      text: "const one = 1;\nconst two = 2;\n",
    },
    {
      id: "chunk-b",
      memoryItemId,
      chunkIndex: 1,
      startLine: 5,
      endLine: 6,
      charCount: 20,
      digest: `sha256:${"c".repeat(64)}`,
      text: "const five = 5;\nconst six = 6;\n",
    },
  ],
};

const hit: VaultFileHit = {
  memoryItemId,
  chunkId: "chunk-b",
  path: "src/app.ts",
  sourceType: "code",
  language: "TypeScript",
  startLine: 5,
  endLine: 6,
};

describe("VaultFileView", () => {
  it("renders line-numbered content, a gap marker, and highlights the hit's chunk", () => {
    const { container } = render(<VaultFileView detail={detail} hit={hit} onBack={vi.fn()} />);

    // Header reflects the passed-through path and line range.
    expect(screen.getByText("src/app.ts")).toBeVisible();
    expect(screen.getByText(/^Matched lines 5.6$/)).toBeVisible();

    // Every indexed line is shown with its true line number in the gutter.
    const gutters = Array.from(container.querySelectorAll(".vault-file-line__no")).map(
      (node) => node.textContent,
    );
    expect(gutters).toEqual(["1", "2", "5", "6"]);

    // Lines 3–4 (dropped/whitespace between chunks) are marked as a gap, not silently skipped.
    expect(screen.getByText(/lines 3.4 not indexed/)).toBeVisible();

    // Only the hit's chunk (lines 5–6) is highlighted.
    expect(screen.getByText("const six = 6;").closest(".vault-file-line")).toHaveClass(
      "vault-file-line--match",
    );
    expect(screen.getByText("const one = 1;").closest(".vault-file-line")).not.toHaveClass(
      "vault-file-line--match",
    );
    expect(container.querySelectorAll(".vault-file-line--match")).toHaveLength(2);
  });

  it("invokes onBack when the back affordance is used", async () => {
    const user = userEvent.setup();
    const onBack = vi.fn();
    render(<VaultFileView detail={detail} hit={hit} onBack={onBack} />);

    await user.click(screen.getByRole("button", { name: /Back to results/ }));
    expect(onBack).toHaveBeenCalledTimes(1);
  });

  it("notes a missing matched region but still renders available content", () => {
    const { container } = render(
      <VaultFileView
        detail={detail}
        hit={{ ...hit, chunkId: "chunk-gone", startLine: 9, endLine: 9 }}
        onBack={vi.fn()}
      />,
    );

    expect(screen.getByText(/Matched lines 9.9 are no longer in this file/)).toBeVisible();
    expect(screen.getByText("const one = 1;")).toBeVisible();
    expect(container.querySelectorAll(".vault-file-line--match")).toHaveLength(0);
  });

  it("shows a bounded message when the item has no indexed content", () => {
    render(
      <VaultFileView detail={{ item: detail.item, chunks: [] }} hit={hit} onBack={vi.fn()} />,
    );

    expect(screen.getByText("No indexed content for this file.")).toBeVisible();
  });
});
