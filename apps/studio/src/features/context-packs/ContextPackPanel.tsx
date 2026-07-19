import type {
  ContextPackCollection,
  ContextPackManifest,
  ContextPackSummary,
  VaultFileCollection,
  VaultFileInventoryItem,
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
const MAX_FILES = 50;
const MAX_PREVIEW_BYTES_PER_FILE = 16 * 1024;
const MAX_TOTAL_PREVIEW_BYTES = 256 * 1024;

export function ContextPackPanel({
  activeWorkspaceId,
}: {
  activeWorkspaceId: string | null;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [selectedPaths, setSelectedPaths] = useState<readonly string[]>([]);
  const [openedPackId, setOpenedPackId] = useState<string | null>(null);

  const inventory = useQuery({
    queryKey: queryKeys.vaultInventory(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) throw new Error("Select a workspace first.");
      return client.getVaultInventory(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });
  const candidates = useQuery({
    queryKey: queryKeys.contextPackCandidates(
      activeWorkspaceId ?? "none",
      inventory.data?.id ?? "none",
    ),
    queryFn: () => {
      if (!activeWorkspaceId) throw new Error("Select a workspace first.");
      return client.listVaultFiles(activeWorkspaceId, { limit: 500 });
    },
    enabled: activeWorkspaceId !== null && inventory.isSuccess,
    retry: false,
  });
  const packs = useQuery({
    queryKey: queryKeys.contextPacks(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) throw new Error("Select a workspace first.");
      return client.listContextPacks(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });
  const manifest = useQuery({
    queryKey: queryKeys.contextPack(
      activeWorkspaceId ?? "none",
      openedPackId ?? "none",
    ),
    queryFn: () => {
      if (!activeWorkspaceId || !openedPackId) {
        throw new Error("Open an immutable context pack first.");
      }
      return client.getContextPack(activeWorkspaceId, openedPackId);
    },
    enabled: activeWorkspaceId !== null && openedPackId !== null,
    retry: false,
  });

  const selectedFiles = useMemo(
    () =>
      candidates.data?.items.filter((file) => selectedPaths.includes(file.path)) ?? [],
    [candidates.data, selectedPaths],
  );
  const estimatedPreviewBytes = selectedFiles.reduce(
    (total, file) =>
      total +
      (file.kind === "text"
        ? Math.min(file.sizeBytes, MAX_PREVIEW_BYTES_PER_FILE)
        : 0),
    0,
  );
  const selectionError = getSelectionError(
    selectedPaths.length,
    estimatedPreviewBytes,
  );

  const create = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) throw new Error("Select a workspace first.");
      return client.createContextPack(activeWorkspaceId, {
        paths: [...selectedPaths].sort((left, right) =>
          left.localeCompare(right, undefined, { sensitivity: "base" }),
        ),
      });
    },
    onSuccess: (response) => {
      const pack = response.contextPack;
      setOpenedPackId(pack.id);
      queryClient.setQueryData(
        queryKeys.contextPack(pack.workspaceId, pack.id),
        pack,
      );
      void queryClient.invalidateQueries({
        queryKey: queryKeys.contextPacks(pack.workspaceId),
        exact: true,
      });
    },
  });

  function togglePath(path: string) {
    setSelectedPaths((current) =>
      current.includes(path)
        ? current.filter((selectedPath) => selectedPath !== path)
        : [...current, path],
    );
    create.reset();
  }

  const inventoryNotBuilt =
    inventory.isError &&
    inventory.error instanceof CoreApiError &&
    inventory.error.problem.type === INVENTORY_NOT_BUILT_TYPE;

  return (
    <Panel eyebrow="Exact execution evidence" title="Context packs">
      {!activeWorkspaceId ? (
        <EmptyState>
          Select an active workspace before assembling immutable context.
        </EmptyState>
      ) : null}
      {activeWorkspaceId && inventory.isPending ? (
        <LoadingState>Loading the current Vault inventory…</LoadingState>
      ) : null}
      {inventoryNotBuilt ? (
        <EmptyState>
          Build a Vault inventory above before selecting context files.
        </EmptyState>
      ) : null}
      {inventory.isError && !inventoryNotBuilt ? (
        <ProblemDetailsView error={inventory.error} />
      ) : null}
      {inventory.isSuccess ? (
        <div className="context-pack-layout">
          <ContextPackBuilder
            files={candidates}
            selectedFiles={selectedFiles}
            selectedPaths={selectedPaths}
            estimatedPreviewBytes={estimatedPreviewBytes}
            selectionError={selectionError}
            onTogglePath={togglePath}
            onCreate={() => create.mutate()}
            isCreating={create.isPending}
          />
          <ContextPackLibrary
            packs={packs}
            openedPackId={openedPackId}
            onOpen={setOpenedPackId}
          />
        </div>
      ) : null}
      {create.isPending ? (
        <div className="context-pack-capturing" role="status">
          <span className="spinner" aria-hidden="true" />
          <span>Core is hashing files and capturing bounded evidence…</span>
        </div>
      ) : null}
      {create.isError ? <ProblemDetailsView error={create.error} /> : null}
      {create.isSuccess ? (
        <p className="success-message" role="status">
          {create.data.created
            ? "Context pack created and locked."
            : "Existing immutable context pack reopened."}
        </p>
      ) : null}
      {openedPackId ? (
        <ContextPackReview manifest={manifest} />
      ) : activeWorkspaceId && inventory.isSuccess ? (
        <EmptyState>Create or open a context pack to review its exact manifest.</EmptyState>
      ) : null}
    </Panel>
  );
}

function ContextPackBuilder({
  files,
  selectedFiles,
  selectedPaths,
  estimatedPreviewBytes,
  selectionError,
  onTogglePath,
  onCreate,
  isCreating,
}: {
  files: UseQueryResult<VaultFileCollection, Error>;
  selectedFiles: readonly VaultFileInventoryItem[];
  selectedPaths: readonly string[];
  estimatedPreviewBytes: number;
  selectionError: string | null;
  onTogglePath: (path: string) => void;
  onCreate: () => void;
  isCreating: boolean;
}) {
  return (
    <section className="context-pack-builder" aria-label="Context pack builder">
      <div className="context-pack-section-heading">
        <div>
          <strong>Select exact files</strong>
          <span>Current Vault inventory · up to {MAX_FILES} files</span>
        </div>
        <button
          className="button button--primary"
          type="button"
          onClick={onCreate}
          disabled={selectedPaths.length === 0 || selectionError !== null || isCreating}
        >
          {isCreating ? "Creating pack…" : "Create immutable pack"}
        </button>
      </div>
      <div className="context-pack-selection-summary" aria-live="polite">
        <span>{selectedPaths.length} selected</span>
        <span>Preview upper bound {formatBytes(estimatedPreviewBytes)}</span>
      </div>
      {selectionError ? (
        <p className="field-error" role="alert">
          {selectionError}
        </p>
      ) : null}
      {files.isPending ? <LoadingState>Loading selectable files…</LoadingState> : null}
      {files.isError ? <ProblemDetailsView error={files.error} /> : null}
      {files.isSuccess && files.data.items.length === 0 ? (
        <EmptyState>The current inventory contains no selectable files.</EmptyState>
      ) : null}
      {files.isSuccess && files.data.items.length > 0 ? (
        <fieldset className="context-pack-candidates">
          <legend>Inventoried files</legend>
          {files.data.items.map((file) => (
            <label key={file.path}>
              <input
                type="checkbox"
                checked={selectedPaths.includes(file.path)}
                onChange={() => onTogglePath(file.path)}
              />
              <span>
                <code>{file.path}</code>
                <small>
                  {file.kind} · {formatBytes(file.sizeBytes)}
                </small>
              </span>
            </label>
          ))}
        </fieldset>
      ) : null}
      {selectedFiles.length ? (
        <div className="context-pack-selected" aria-label="Selected context files">
          <strong>Exact selection before creation</strong>
          <ol>
            {selectedFiles.map((file) => (
              <li key={file.path}>
                <code>{file.path}</code>
                <span>{file.kind === "text" ? "bounded preview" : "metadata only"}</span>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}

function ContextPackLibrary({
  packs,
  openedPackId,
  onOpen,
}: {
  packs: UseQueryResult<ContextPackCollection, Error>;
  openedPackId: string | null;
  onOpen: (id: string) => void;
}) {
  return (
    <section className="context-pack-library" aria-label="Immutable context packs">
      <div className="context-pack-section-heading">
        <div>
          <strong>Immutable packs</strong>
          <span>{packs.data?.total ?? 0} in Core memory</span>
        </div>
      </div>
      {packs.isPending ? <LoadingState>Loading context packs…</LoadingState> : null}
      {packs.isError ? <ProblemDetailsView error={packs.error} /> : null}
      {packs.isSuccess && packs.data.items.length === 0 ? (
        <EmptyState>No context packs have been created in this Core session.</EmptyState>
      ) : null}
      {packs.isSuccess && packs.data.items.length > 0 ? (
        <ul className="context-pack-list">
          {packs.data.items.map((pack) => (
            <li key={pack.id}>
              <button
                type="button"
                aria-pressed={openedPackId === pack.id}
                onClick={() => onOpen(pack.id)}
              >
                <span>
                  <code>{shortDigest(pack.id)}</code>
                  <small>{pack.summary.fileCount} files</small>
                </span>
                <span className="badge">Open</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

function ContextPackReview({
  manifest,
}: {
  manifest: UseQueryResult<ContextPackManifest, Error>;
}) {
  if (manifest.isPending) return <LoadingState>Loading immutable manifest…</LoadingState>;
  if (manifest.isError) return <ProblemDetailsView error={manifest.error} />;
  if (!manifest.data) return null;

  const pack = manifest.data;
  return (
    <section className="context-pack-review" aria-label="Context pack manifest">
      <div className="context-pack-review__heading">
        <div>
          <span>Read-only manifest · schema {pack.schemaVersion}</span>
          <strong>Immutable context pack</strong>
        </div>
        <span className="badge badge--clean">Locked</span>
      </div>
      <dl className="context-pack-identity">
        <div>
          <dt>Pack id / digest</dt>
          <dd>
            <code>{pack.id}</code>
          </dd>
        </div>
        <div>
          <dt>Inventory snapshot</dt>
          <dd>
            <code>{pack.inventoryId}</code>
          </dd>
        </div>
      </dl>
      <dl className="context-pack-counts">
        <SummaryValue label="Files" value={String(pack.summary.fileCount)} />
        <SummaryValue label="Text" value={String(pack.summary.textFileCount)} />
        <SummaryValue label="Binary" value={String(pack.summary.binaryFileCount)} />
        <SummaryValue label="File bytes" value={formatBytes(pack.summary.totalFileBytes)} />
        <SummaryValue
          label="Preview bytes"
          value={formatBytes(pack.summary.totalPreviewBytes)}
        />
        <SummaryValue
          label="Truncated"
          value={String(pack.summary.truncatedTextFileCount)}
        />
      </dl>
      <ol className="context-pack-manifest-files">
        {pack.files.map((file) => (
          <li key={file.path}>
            <div>
              <code>{file.path}</code>
              <span>
                {file.captureMode === "text_preview" ? "Text preview" : "Metadata only"}
                {file.truncated ? " · truncated" : ""}
              </span>
            </div>
            <dl>
              <div>
                <dt>Content digest</dt>
                <dd>
                  <code>{file.contentDigest}</code>
                </dd>
              </div>
              <div>
                <dt>Captured</dt>
                <dd>
                  {formatBytes(file.previewBytes)} of {formatBytes(file.totalBytes)}
                </dd>
              </div>
            </dl>
          </li>
        ))}
      </ol>
    </section>
  );
}

function SummaryValue({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function getSelectionError(fileCount: number, previewBytes: number) {
  if (fileCount > MAX_FILES) return `Select at most ${MAX_FILES} files.`;
  if (previewBytes > MAX_TOTAL_PREVIEW_BYTES) {
    return "Selected text previews exceed the 256 KiB pack limit.";
  }
  return null;
}

function shortDigest(pack: ContextPackSummary["id"]) {
  return `${pack.slice(0, 19)}…`;
}

function formatBytes(bytes: number) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KiB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MiB`;
}
