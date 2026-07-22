import type { VaultFileInventoryItem } from "@mensura/shared-types";
import { describe, expect, it } from "vitest";

import {
  ancestorDirectoryPaths,
  buildFileTree,
  classifyFile,
  collectDirectoryPaths,
  type FileTreeNode,
} from "./fileTree";

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

describe("classifyFile", () => {
  it("labels source files as code", () => {
    expect(classifyFile(item("src/app.ts", { language: "TypeScript" }))).toBe("code");
    expect(classifyFile(item("main.py"))).toBe("code");
  });

  it("labels documentation extensions as doc", () => {
    expect(classifyFile(item("README.md", { language: "Markdown" }))).toBe("doc");
    expect(classifyFile(item("docs/guide.rst"))).toBe("doc");
  });

  it("prefers config over a language for config formats", () => {
    // The inventory may assign JSON a language, but it reads as config here.
    expect(classifyFile(item("package.json", { language: "JSON" }))).toBe("config");
    expect(classifyFile(item("Dockerfile"))).toBe("config");
  });

  it("labels binary files as binary regardless of extension", () => {
    expect(classifyFile(item("assets/logo.png", { kind: "binary" }))).toBe("binary");
  });

  it("falls back to text for unknown extensionless files", () => {
    expect(classifyFile(item("LICENSE"))).toBe("text");
  });
});

describe("buildFileTree", () => {
  const tree = buildFileTree([
    item("src/app.ts"),
    item("src/util/math.ts"),
    item("README.md"),
    item("src/app.test.ts"),
  ]);

  it("nests files under synthesised directories", () => {
    expect(tree.map((node) => `${node.kind}:${node.name}`)).toEqual([
      "directory:src",
      "file:README.md",
    ]);
    const src = tree[0] as Extract<FileTreeNode, { kind: "directory" }>;
    expect(src.children.map((node) => `${node.kind}:${node.name}`)).toEqual([
      "directory:util",
      "file:app.test.ts",
      "file:app.ts",
    ]);
  });

  it("keeps directories before files and sorts each group", () => {
    const src = tree[0] as Extract<FileTreeNode, { kind: "directory" }>;
    const util = src.children[0] as Extract<FileTreeNode, { kind: "directory" }>;
    expect(util.path).toBe("src/util");
    expect(util.children.map((node) => node.name)).toEqual(["math.ts"]);
  });

  it("collects every directory path for default expansion", () => {
    expect(collectDirectoryPaths(tree)).toEqual(["src", "src/util"]);
  });
});

describe("ancestorDirectoryPaths", () => {
  it("returns each ancestor directory nearest-root first", () => {
    expect(ancestorDirectoryPaths("src/util/math.ts")).toEqual(["src", "src/util"]);
  });

  it("returns nothing for a root-level file", () => {
    expect(ancestorDirectoryPaths("README.md")).toEqual([]);
  });
});
