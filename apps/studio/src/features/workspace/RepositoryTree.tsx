import type { VaultFileInventoryItem } from "@mensura/shared-types";
import { type ReactNode, useEffect, useState } from "react";

import {
  ancestorDirectoryPaths,
  collectDirectoryPaths,
  type FileTreeNode,
  type WorkspaceFileType,
} from "./fileTree";

const FILE_TYPE_BADGE: Record<
  WorkspaceFileType,
  { label: string; className: string }
> = {
  code: { label: "code", className: "badge" },
  doc: { label: "doc", className: "badge badge--clean" },
  config: { label: "cfg", className: "badge badge--dirty" },
  binary: { label: "bin", className: "badge badge--error" },
  text: { label: "txt", className: "badge" },
};

const INDENT_REM = 0.85;

export function RepositoryTree({
  nodes,
  selectedPath,
  onSelectFile,
  revealPath,
}: {
  nodes: FileTreeNode[];
  selectedPath: string | null;
  onSelectFile: (file: VaultFileInventoryItem) => void;
  /** When set, its ancestor directories are expanded so the file is visible. */
  revealPath?: string | null;
}) {
  const [expanded, setExpanded] = useState<Set<string>>(
    () => new Set(collectDirectoryPaths(nodes)),
  );

  // A new inventory (new tree identity) resets expansion to fully open.
  useEffect(() => {
    setExpanded(new Set(collectDirectoryPaths(nodes)));
  }, [nodes]);

  // Reveal a requested file by expanding its ancestor directories.
  useEffect(() => {
    if (!revealPath) return;
    setExpanded((previous) => {
      const next = new Set(previous);
      for (const directory of ancestorDirectoryPaths(revealPath)) {
        next.add(directory);
      }
      return next;
    });
  }, [revealPath]);

  const toggle = (path: string) => {
    setExpanded((previous) => {
      const next = new Set(previous);
      if (next.has(path)) {
        next.delete(path);
      } else {
        next.add(path);
      }
      return next;
    });
  };

  const renderNode = (node: FileTreeNode, depth: number): ReactNode => {
    const indent = `${depth * INDENT_REM + 0.4}rem`;
    if (node.kind === "directory") {
      const isOpen = expanded.has(node.path);
      return (
        <li key={node.path} role="treeitem" aria-expanded={isOpen}>
          <button
            type="button"
            className="workspace-tree__dir"
            style={{ paddingLeft: indent }}
            onClick={() => toggle(node.path)}
          >
            <span className="workspace-tree__twist" aria-hidden="true">
              {isOpen ? "▾" : "▸"}
            </span>
            <span className="workspace-tree__name">{node.name}</span>
          </button>
          {isOpen ? (
            <ul role="group">
              {node.children.map((child) => renderNode(child, depth + 1))}
            </ul>
          ) : null}
        </li>
      );
    }

    const badge = FILE_TYPE_BADGE[node.fileType];
    const selected = node.path === selectedPath;
    return (
      <li key={node.path} role="treeitem" aria-selected={selected}>
        <button
          type="button"
          className="workspace-tree__file"
          aria-pressed={selected}
          style={{ paddingLeft: indent }}
          onClick={() => onSelectFile(node.file)}
        >
          <span className="workspace-tree__name">{node.name}</span>
          <span className={badge.className}>{badge.label}</span>
        </button>
      </li>
    );
  };

  return (
    <ul className="workspace-tree" role="tree" aria-label="Repository files">
      {nodes.map((node) => renderNode(node, 0))}
    </ul>
  );
}
