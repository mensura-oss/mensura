import type { VaultMemoryItemDetail, VaultSourceType } from "@mensura/shared-types";
import { useEffect, useMemo, useRef } from "react";

import type { OpenInWorkspaceHandler } from "../workspace/types";

/**
 * The subset of a search hit needed to open and anchor a file view. It carries
 * the hit's own `startLine`/`endLine`/`chunkId` so the matched region can be
 * highlighted before (and independently of) the memory-item detail loading.
 */
export interface VaultFileHit {
  memoryItemId: string;
  chunkId: string;
  path: string;
  sourceType: VaultSourceType;
  language: string | null;
  startLine: number;
  endLine: number;
}

type FileRow =
  | {
      kind: "line";
      key: string;
      lineNumber: number;
      text: string;
      match: boolean;
      firstMatch: boolean;
    }
  | { kind: "gap"; key: string; fromLine: number; toLine: number };

interface BuiltFile {
  rows: FileRow[];
  matchPresent: boolean;
}

/**
 * Minimal read-only file view for a Vault search hit. It reconstructs a
 * line-numbered rendering of the file from the memory item's indexed chunks
 * (same durable snapshot the hit came from, so line ranges always align),
 * highlights the hit's line block, and scrolls the first matched line into
 * view. It is deliberately NOT an editor: no editing, syntax highlighting,
 * multi-file tabs, or live re-read.
 */
export function VaultFileView({
  detail,
  hit,
  onBack,
  onOpenInWorkspace,
}: {
  detail: VaultMemoryItemDetail;
  hit: VaultFileHit;
  onBack: () => void;
  /** When provided, offers to open this hit in the Workspace editor at its lines. */
  onOpenInWorkspace?: OpenInWorkspaceHandler | undefined;
}) {
  const firstMatchRef = useRef<HTMLDivElement | null>(null);
  const { rows, matchPresent } = useMemo(
    () => buildFile(detail, hit.chunkId),
    [detail, hit.chunkId],
  );

  useEffect(() => {
    // jsdom (tests) has no scrollIntoView — guard so the view still renders.
    firstMatchRef.current?.scrollIntoView?.({ block: "center", behavior: "auto" });
  }, [detail, hit.chunkId]);

  const item = detail.item;

  return (
    <div className="vault-file-view">
      <div className="vault-file-view__bar">
        <button type="button" className="button button--quiet" onClick={onBack}>
          ← Back to results
        </button>
        {onOpenInWorkspace ? (
          <button
            type="button"
            className="button button--secondary"
            onClick={() =>
              onOpenInWorkspace({
                path: hit.path,
                startLine: hit.startLine,
                endLine: hit.endLine,
              })
            }
          >
            Open in Workspace editor →
          </button>
        ) : null}
      </div>
      <div className="vault-file-view__head">
        <code className="vault-file-view__path">{hit.path}</code>
        <span className="vault-file-view__meta">
          <span className="badge">{hit.sourceType}</span>
          {hit.language ? <span className="badge">{hit.language}</span> : null}
          <span className="badge badge--clean">
            Matched lines {hit.startLine}–{hit.endLine}
          </span>
          <span>
            {formatBytes(item.sizeBytes)} · {item.chunkCount} chunk
            {item.chunkCount === 1 ? "" : "s"}
          </span>
        </span>
      </div>
      {!matchPresent && rows.length > 0 ? (
        <p className="vault-file-view__note" role="status">
          Matched lines {hit.startLine}–{hit.endLine} are no longer in this file&apos;s indexed
          content. Showing the available indexed lines below.
        </p>
      ) : null}
      {rows.length === 0 ? (
        <p className="vault-file-view__note">No indexed content for this file.</p>
      ) : (
        <div
          className="vault-file-view__code"
          role="group"
          aria-label={`Contents of ${hit.path}`}
        >
          {rows.map((row) =>
            row.kind === "gap" ? (
              <div className="vault-file-gap" key={row.key} aria-hidden="true">
                ⋯ lines {row.fromLine}–{row.toLine} not indexed ⋯
              </div>
            ) : (
              <div
                className={`vault-file-line${row.match ? " vault-file-line--match" : ""}`}
                key={row.key}
                ref={row.firstMatch ? firstMatchRef : null}
                data-line={row.lineNumber}
              >
                <span className="vault-file-line__no" aria-hidden="true">
                  {row.lineNumber}
                </span>
                <code className="vault-file-line__text">
                  {row.text === "" ? " " : row.text}
                </code>
              </div>
            ),
          )}
        </div>
      )}
      <p className="vault-index-hint">
        Read-only file view reconstructed from the durable Vault index (not a live re-read of the
        working tree). No editing, syntax highlighting, or multi-file tabs yet.
      </p>
    </div>
  );
}

/**
 * Concatenate a memory item's chunks into ordered, line-numbered rows.
 * Non-contiguous chunks (docs drop whitespace-only chunks; code past the
 * per-file chunk cap) produce an explicit gap marker so line numbers stay
 * honest. Lines belonging to the hit's chunk are flagged `match`, and the very
 * first such line is flagged `firstMatch` for scroll anchoring.
 */
function buildFile(detail: VaultMemoryItemDetail, activeChunkId: string): BuiltFile {
  const chunks = [...detail.chunks].sort((a, b) => a.chunkIndex - b.chunkIndex);
  const rows: FileRow[] = [];
  let matchPresent = false;
  let firstMatchAssigned = false;
  let prevEndLine: number | null = null;

  for (const chunk of chunks) {
    if (prevEndLine !== null && chunk.startLine > prevEndLine + 1) {
      rows.push({
        kind: "gap",
        key: `gap-${prevEndLine}-${chunk.startLine}`,
        fromLine: prevEndLine + 1,
        toLine: chunk.startLine - 1,
      });
    }

    const lines = splitChunkLines(chunk.text);
    // Overlap guard: never emit a line number already rendered by a prior chunk.
    const startOffset =
      prevEndLine !== null && chunk.startLine <= prevEndLine
        ? prevEndLine - chunk.startLine + 1
        : 0;
    const isMatchChunk = chunk.id === activeChunkId;

    for (let i = startOffset; i < lines.length; i += 1) {
      const lineNumber = chunk.startLine + i;
      const firstMatch = isMatchChunk && !firstMatchAssigned;
      if (isMatchChunk) matchPresent = true;
      if (firstMatch) firstMatchAssigned = true;
      rows.push({
        kind: "line",
        key: `${chunk.id}-${lineNumber}`,
        lineNumber,
        text: lines[i] ?? "",
        match: isMatchChunk,
        firstMatch,
      });
    }

    const lastLineNumber = chunk.startLine + Math.max(lines.length - 1, 0);
    prevEndLine = Math.max(chunk.endLine, lastLineNumber, prevEndLine ?? 0);
  }

  return { rows, matchPresent };
}

/** Split chunk text into lines, dropping the single trailing empty line from a terminal newline. */
function splitChunkLines(text: string): string[] {
  const lines = text.split("\n");
  if (lines.length > 0 && lines[lines.length - 1] === "") {
    lines.pop();
  }
  return lines;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
