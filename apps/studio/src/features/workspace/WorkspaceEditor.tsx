import type { VaultFileInventoryItem } from "@mensura/shared-types";
import { useQuery } from "@tanstack/react-query";
import { Suspense, lazy, useMemo } from "react";

import { useCoreClient } from "../../api/CoreClientProvider";
import { CoreApiError } from "../../api/coreClient";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { monacoLanguageForFile } from "./languages";
import type { MonacoHighlight } from "./MonacoCodeViewer";

const MonacoCodeViewer = lazy(() => import("./MonacoCodeViewer"));

const BINARY_PREVIEW_TYPE = "urn:mensura:problem:vault-binary-preview-refused";
const FILE_EXCLUDED_TYPE = "urn:mensura:problem:vault-file-excluded";
const INVENTORY_NOT_BUILT_TYPE = "urn:mensura:problem:vault-inventory-not-built";

export function WorkspaceEditor({
  workspaceId,
  path,
  file,
  highlight,
}: {
  workspaceId: string;
  /** Selected workspace-relative path, or null when nothing is open. */
  path: string | null;
  /** Tree metadata for the path when known (drives the binary short-circuit). */
  file: VaultFileInventoryItem | null;
  highlight?: MonacoHighlight | null;
}) {
  const client = useCoreClient();
  const isKnownBinary = file?.kind === "binary";

  const preview = useQuery({
    queryKey: queryKeys.vaultFilePreview(workspaceId, path ?? "none"),
    queryFn: () => {
      if (!path) {
        throw new Error("Select a file before loading its contents.");
      }
      return client.getVaultFilePreview(workspaceId, path);
    },
    enabled: path !== null && !isKnownBinary,
    retry: false,
  });

  const language = useMemo(() => {
    if (!path) return "plaintext";
    const label = preview.data?.file.language ?? file?.language ?? null;
    return monacoLanguageForFile(path, label);
  }, [path, preview.data, file]);

  if (!path) {
    return (
      <EmptyState>
        Select a file from the repository tree to view it here.
      </EmptyState>
    );
  }

  const header = (
    <div className="workspace-editor__head">
      <code className="workspace-editor__path">{path}</code>
      <span className="workspace-editor__meta">
        <span className="badge">Read-only</span>
        {highlight ? (
          <span className="badge badge--clean">
            Lines {highlight.startLine}–{highlight.endLine}
          </span>
        ) : null}
      </span>
    </div>
  );

  if (isKnownBinary) {
    return (
      <div className="workspace-editor">
        {header}
        <EmptyState>
          This is a binary file. The Workspace editor only renders text files.
        </EmptyState>
      </div>
    );
  }

  return (
    <div className="workspace-editor">
      {header}
      {preview.isPending ? <LoadingState>Loading file…</LoadingState> : null}
      {preview.isError ? <EditorError error={preview.error} /> : null}
      {preview.isSuccess ? (
        <EditorContent
          text={preview.data.text}
          language={language}
          highlight={highlight}
          truncated={preview.data.truncated}
          previewBytes={preview.data.previewBytes}
          totalBytes={preview.data.totalBytes}
        />
      ) : null}
    </div>
  );
}

function EditorContent({
  text,
  language,
  highlight,
  truncated,
  previewBytes,
  totalBytes,
}: {
  text: string;
  language: string;
  highlight: MonacoHighlight | null | undefined;
  truncated: boolean;
  previewBytes: number;
  totalBytes: number;
}) {
  const lineCount = useMemo(() => text.split("\n").length, [text]);
  const highlightBeyondPreview =
    highlight != null && highlight.startLine > lineCount;

  return (
    <>
      {truncated ? (
        <p className="workspace-editor__note" role="status">
          Showing the first {formatBytes(previewBytes)} of {formatBytes(totalBytes)} —
          this file is truncated for preview.
        </p>
      ) : null}
      {highlightBeyondPreview ? (
        <p className="workspace-editor__note" role="status">
          Matched lines {highlight!.startLine}–{highlight!.endLine} are beyond the loaded
          preview.
        </p>
      ) : null}
      <Suspense fallback={<LoadingState>Loading editor…</LoadingState>}>
        <MonacoCodeViewer
          value={text}
          language={language}
          highlight={highlightBeyondPreview ? null : (highlight ?? null)}
        />
      </Suspense>
    </>
  );
}

function EditorError({ error }: { error: unknown }) {
  if (error instanceof CoreApiError) {
    const type = error.problem.type;
    if (type === BINARY_PREVIEW_TYPE) {
      return (
        <EmptyState>
          This file looks binary once read, so it cannot be shown as text.
        </EmptyState>
      );
    }
    if (type === FILE_EXCLUDED_TYPE) {
      return (
        <EmptyState>
          This file is too large or excluded from preview by Vault&apos;s rules.
        </EmptyState>
      );
    }
    if (type === INVENTORY_NOT_BUILT_TYPE) {
      return (
        <EmptyState>
          Build the workspace inventory to open files in the editor.
        </EmptyState>
      );
    }
  }
  return <ProblemDetailsView error={error} />;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
