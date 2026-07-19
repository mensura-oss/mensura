import type {
  VaultFileCollection,
  VaultFileInventoryItem,
  VaultFilePreview,
  VaultInventorySnapshot,
} from "@mensura/shared-types";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useMemo, useState } from "react";

import { useCoreClient } from "../../api/CoreClientProvider";
import { CoreApiError } from "../../api/coreClient";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";

const INVENTORY_NOT_BUILT_TYPE = "urn:mensura:problem:vault-inventory-not-built";
const FILE_LIMIT = 200;

export function VaultPanel({
  activeWorkspaceId,
}: {
  activeWorkspaceId: string | null;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const inventory = useQuery({
    queryKey: queryKeys.vaultInventory(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before loading its Vault inventory.");
      }
      return client.getVaultInventory(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });
  const files = useQuery({
    queryKey: queryKeys.vaultFiles(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before loading Vault files.");
      }
      return client.listVaultFiles(activeWorkspaceId, { limit: FILE_LIMIT });
    },
    enabled: activeWorkspaceId !== null && inventory.isSuccess,
    retry: false,
  });
  const build = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before building a Vault inventory.");
      }
      return client.buildVaultInventory(activeWorkspaceId);
    },
    onSuccess: (snapshot) => {
      setSelectedPath(null);
      queryClient.setQueryData(queryKeys.vaultInventory(snapshot.workspaceId), snapshot);
      queryClient.removeQueries({
        queryKey: ["core", "workspaces", snapshot.workspaceId, "vault", "files", "content"],
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.vaultFiles(snapshot.workspaceId),
      });
    },
  });
  const selectedFile = useMemo(
    () => files.data?.items.find((item) => item.path === selectedPath) ?? null,
    [files.data, selectedPath],
  );
  const preview = useQuery({
    queryKey: queryKeys.vaultFilePreview(
      activeWorkspaceId ?? "none",
      selectedPath ?? "none",
    ),
    queryFn: () => {
      if (!activeWorkspaceId || !selectedPath) {
        throw new Error("Select an inventoried text file before loading a preview.");
      }
      return client.getVaultFilePreview(activeWorkspaceId, selectedPath);
    },
    enabled:
      activeWorkspaceId !== null &&
      selectedPath !== null &&
      selectedFile?.kind === "text",
    retry: false,
  });
  const notBuilt = inventory.isError && isInventoryNotBuilt(inventory.error);

  return (
    <Panel
      eyebrow="Deterministic context"
      title="Vault inventory"
      toolbar={
        activeWorkspaceId && !inventory.isPending ? (
          <button
            className="button button--primary"
            type="button"
            onClick={() => build.mutate()}
            disabled={build.isPending}
          >
            {build.isPending
              ? "Building inventory…"
              : inventory.isSuccess
                ? "Refresh inventory"
                : "Build inventory"}
          </button>
        ) : undefined
      }
    >
      {!activeWorkspaceId ? (
        <EmptyState>Select an active workspace to build its Vault inventory.</EmptyState>
      ) : null}
      {activeWorkspaceId && inventory.isPending ? (
        <LoadingState>Loading Vault inventory…</LoadingState>
      ) : null}
      {notBuilt ? (
        <EmptyState>No Vault inventory yet. Build one to inspect repository files.</EmptyState>
      ) : null}
      {inventory.isError && !notBuilt ? (
        <ProblemDetailsView error={inventory.error} />
      ) : null}
      {build.isPending ? (
        <div className="vault-building" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Core is traversing the workspace with fixed exclusion rules…</span>
        </div>
      ) : null}
      {build.isError ? <ProblemDetailsView error={build.error} /> : null}
      {inventory.isSuccess ? (
        <VaultReadyContent
          inventory={inventory.data}
          files={files}
          selectedFile={selectedFile}
          selectedPath={selectedPath}
          onSelectPath={setSelectedPath}
          preview={preview}
        />
      ) : null}
    </Panel>
  );
}

function isInventoryNotBuilt(error: unknown) {
  return error instanceof CoreApiError && error.problem.type === INVENTORY_NOT_BUILT_TYPE;
}

function VaultReadyContent({
  inventory,
  files,
  selectedFile,
  selectedPath,
  onSelectPath,
  preview,
}: {
  inventory: VaultInventorySnapshot;
  files: UseQueryResult<VaultFileCollection, Error>;
  selectedFile: VaultFileInventoryItem | null;
  selectedPath: string | null;
  onSelectPath: (path: string) => void;
  preview: UseQueryResult<VaultFilePreview, Error>;
}) {
  return (
    <div className="vault-ready">
      <VaultSummary inventory={inventory} />
      <div className="vault-browser">
        <section className="vault-files" aria-label="Inventoried files">
          <div className="vault-section-heading">
            <strong>Files</strong>
            {files.isSuccess ? (
              <span>
                {files.data.returned} of {files.data.total}
              </span>
            ) : null}
          </div>
          {files.isPending ? <LoadingState>Loading file metadata…</LoadingState> : null}
          {files.isError ? <ProblemDetailsView error={files.error} /> : null}
          {files.isSuccess && files.data.items.length === 0 ? (
            <EmptyState>No files matched the current inventory.</EmptyState>
          ) : null}
          {files.isSuccess && files.data.items.length > 0 ? (
            <ul className="vault-file-list">
              {files.data.items.map((file) => (
                <li key={file.path}>
                  <button
                    type="button"
                    aria-pressed={selectedPath === file.path}
                    onClick={() => onSelectPath(file.path)}
                  >
                    <span>{file.path}</span>
                    <small>{file.kind}</small>
                  </button>
                </li>
              ))}
            </ul>
          ) : null}
        </section>
        <section className="vault-inspector" aria-label="Vault file inspector">
          <div className="vault-section-heading">
            <strong>File inspector</strong>
          </div>
          {!selectedFile ? <EmptyState>Select a file to inspect its metadata.</EmptyState> : null}
          {selectedFile ? (
            <>
              <VaultFileMetadata file={selectedFile} />
              {selectedFile.kind === "binary" ? (
                <EmptyState>
                  Binary files are inventoried as metadata, but text preview is unavailable.
                </EmptyState>
              ) : null}
              {selectedFile.kind === "text" && preview.isPending ? (
                <LoadingState>Loading bounded text preview…</LoadingState>
              ) : null}
              {selectedFile.kind === "text" && preview.isError ? (
                <ProblemDetailsView error={preview.error} />
              ) : null}
              {selectedFile.kind === "text" && preview.isSuccess ? (
                <VaultPreviewContent preview={preview.data} />
              ) : null}
            </>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function VaultSummary({ inventory }: { inventory: VaultInventorySnapshot }) {
  const summary = inventory.summary;
  return (
    <div className="vault-summary">
      <dl className="vault-counts">
        <div>
          <dt>Included</dt>
          <dd>{summary.includedFileCount}</dd>
        </div>
        <div>
          <dt>Excluded</dt>
          <dd>{summary.excludedEntryCount}</dd>
        </div>
        <div>
          <dt>Text</dt>
          <dd>{summary.textFileCount}</dd>
        </div>
        <div>
          <dt>Binary</dt>
          <dd>{summary.binaryFileCount}</dd>
        </div>
        <div>
          <dt>Size</dt>
          <dd>{formatBytes(summary.totalSizeBytes)}</dd>
        </div>
      </dl>
      <div className="vault-languages">
        <span>Languages</span>
        <div>
          {summary.languages.length ? (
            summary.languages.slice(0, 6).map((language) => (
              <span className="badge" key={language.value}>
                {language.value} {language.count}
              </span>
            ))
          ) : (
            <small>None detected</small>
          )}
        </div>
      </div>
    </div>
  );
}

function VaultFileMetadata({ file }: { file: VaultFileInventoryItem }) {
  return (
    <dl className="vault-file-metadata">
      <div>
        <dt>Path</dt>
        <dd>
          <code>{file.path}</code>
        </dd>
      </div>
      <div>
        <dt>Kind</dt>
        <dd>{file.kind}</dd>
      </div>
      <div>
        <dt>Language</dt>
        <dd>{file.language ?? "—"}</dd>
      </div>
      <div>
        <dt>Size</dt>
        <dd>{formatBytes(file.sizeBytes)}</dd>
      </div>
    </dl>
  );
}

function VaultPreviewContent({ preview }: { preview: VaultFilePreview }) {
  return (
    <div className="vault-preview">
      <div>
        <span>UTF-8 preview</span>
        <span>
          {formatBytes(preview.previewBytes)} of {formatBytes(preview.totalBytes)}
          {preview.truncated ? " · truncated" : ""}
        </span>
      </div>
      <pre>{preview.text}</pre>
    </div>
  );
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
