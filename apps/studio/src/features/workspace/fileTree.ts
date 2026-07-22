import type { VaultFileInventoryItem } from "@mensura/shared-types";

/**
 * Coarse, display-only classification for a repository file. Drives the small
 * badge shown next to a leaf in the tree — it is a hint, not a guarantee, and
 * deliberately has only a handful of buckets.
 */
export type WorkspaceFileType = "code" | "doc" | "config" | "binary" | "text";

export type FileTreeNode =
  | {
      kind: "directory";
      /** Trailing path segment, e.g. `routers`. */
      name: string;
      /** Full workspace-relative posix path, e.g. `services/core/api/routers`. */
      path: string;
      children: FileTreeNode[];
    }
  | {
      kind: "file";
      name: string;
      path: string;
      file: VaultFileInventoryItem;
      fileType: WorkspaceFileType;
    };

const DOC_EXTENSIONS = new Set([
  ".md",
  ".mdx",
  ".markdown",
  ".rst",
  ".txt",
  ".adoc",
]);

const CONFIG_EXTENSIONS = new Set([
  ".json",
  ".jsonc",
  ".yaml",
  ".yml",
  ".toml",
  ".ini",
  ".cfg",
  ".conf",
  ".env",
  ".lock",
  ".properties",
  ".editorconfig",
  ".xml",
]);

const CONFIG_NAMES = new Set([
  "dockerfile",
  "makefile",
  ".gitignore",
  ".dockerignore",
  ".gitattributes",
  ".npmrc",
  ".nvmrc",
]);

const CODE_EXTENSIONS = new Set([
  ".ts",
  ".tsx",
  ".mts",
  ".cts",
  ".js",
  ".jsx",
  ".mjs",
  ".cjs",
  ".py",
  ".rs",
  ".go",
  ".java",
  ".rb",
  ".c",
  ".h",
  ".cc",
  ".cpp",
  ".hpp",
  ".cs",
  ".php",
  ".swift",
  ".kt",
  ".sh",
  ".bash",
  ".sql",
  ".css",
  ".scss",
  ".less",
  ".html",
  ".htm",
  ".vue",
  ".svelte",
]);

/**
 * Bucket a file for its display badge. Documentation and configuration
 * extensions are checked before the inventory `language`, because the inventory
 * may label config formats (e.g. JSON) with a language even though they read as
 * config to a developer scanning the tree.
 */
export function classifyFile(item: VaultFileInventoryItem): WorkspaceFileType {
  if (item.kind === "binary") return "binary";
  const name = item.name.toLowerCase();
  const extension = item.extension?.toLowerCase() ?? "";
  if (CONFIG_NAMES.has(name)) return "config";
  if (extension && DOC_EXTENSIONS.has(extension)) return "doc";
  if (extension && CONFIG_EXTENSIONS.has(extension)) return "config";
  if (item.language || (extension && CODE_EXTENSIONS.has(extension))) return "code";
  return "text";
}

/**
 * Fold a flat, posix-relative inventory listing into a nested directory tree.
 * Directories are synthesised from path segments; files land at their leaf.
 * Output is stably sorted (directories first, then files, case-insensitive) so
 * the rendered tree is deterministic across inventory rebuilds.
 */
export function buildFileTree(
  items: readonly VaultFileInventoryItem[],
): FileTreeNode[] {
  const root: FileTreeNode[] = [];
  const directoryChildren = new Map<string, FileTreeNode[]>();
  directoryChildren.set("", root);

  const ensureDirectory = (segments: readonly string[]): FileTreeNode[] => {
    let currentPath = "";
    let children = root;
    for (const segment of segments) {
      const parentPath = currentPath;
      currentPath = parentPath ? `${parentPath}/${segment}` : segment;
      let bucket = directoryChildren.get(currentPath);
      if (!bucket) {
        bucket = [];
        directoryChildren.set(currentPath, bucket);
        children.push({
          kind: "directory",
          name: segment,
          path: currentPath,
          children: bucket,
        });
      }
      children = bucket;
    }
    return children;
  };

  for (const item of items) {
    const segments = item.path.split("/").filter((segment) => segment.length > 0);
    if (segments.length === 0) continue;
    const fileName = segments[segments.length - 1]!;
    const bucket = ensureDirectory(segments.slice(0, -1));
    bucket.push({
      kind: "file",
      name: fileName,
      path: item.path,
      file: item,
      fileType: classifyFile(item),
    });
  }

  sortNodes(root);
  return root;
}

function sortNodes(nodes: FileTreeNode[]): void {
  nodes.sort((a, b) => {
    if (a.kind !== b.kind) return a.kind === "directory" ? -1 : 1;
    return a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
  });
  for (const node of nodes) {
    if (node.kind === "directory") sortNodes(node.children);
  }
}

/** Every directory path in the tree — used to expand the tree fully by default. */
export function collectDirectoryPaths(nodes: readonly FileTreeNode[]): string[] {
  const paths: string[] = [];
  const walk = (list: readonly FileTreeNode[]) => {
    for (const node of list) {
      if (node.kind === "directory") {
        paths.push(node.path);
        walk(node.children);
      }
    }
  };
  walk(nodes);
  return paths;
}

/** Ancestor directory paths of a file, nearest-root first — used to reveal it. */
export function ancestorDirectoryPaths(filePath: string): string[] {
  const segments = filePath.split("/").filter((segment) => segment.length > 0);
  const directories: string[] = [];
  let current = "";
  for (let index = 0; index < segments.length - 1; index += 1) {
    current = current ? `${current}/${segments[index]}` : segments[index]!;
    directories.push(current);
  }
  return directories;
}
