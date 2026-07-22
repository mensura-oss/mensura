import type {
  RepositorySummary,
  VaultFileInventoryItem,
  VaultIndexSnapshot,
} from "@mensura/shared-types";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryResult,
} from "@tanstack/react-query";
import { useEffect, useMemo, useRef, useState } from "react";

import { useCoreClient } from "../../api/CoreClientProvider";
import { CoreApiError } from "../../api/coreClient";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { buildFileTree } from "./fileTree";
import type { MonacoHighlight } from "./MonacoCodeViewer";
import { RepositoryTree } from "./RepositoryTree";
import { TaskBoardPanel } from "./TaskBoardPanel";
import type { WorkspaceOpenRequest } from "./types";
import { WorkspaceEditor } from "./WorkspaceEditor";

const INVENTORY_NOT_BUILT_TYPE = "urn:mensura:problem:vault-inventory-not-built";
const INDEX_NOT_BUILT_TYPE = "urn:mensura:problem:vault-index-not-built";
const NOT_A_GIT_REPOSITORY_TYPE = "urn:mensura:problem:not-a-git-repository";
const FILE_LIMIT = 500;

export function WorkspacePanel({
  activeWorkspaceId,
  openRequest,
}: {
  activeWorkspaceId: string | null;
  /** A cross-panel request (from Vault) to open a file in the editor. */
  openRequest?: WorkspaceOpenRequest | null;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const containerRef = useRef<HTMLDivElement | null>(null);

  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [highlight, setHighlight] = useState<MonacoHighlight | null>(null);
  const [revealPath, setRevealPath] = useState<string | null>(null);

  const repository = useQuery({
    queryKey: queryKeys.workspaceRepository(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before inspecting its repository.");
      }
      return client.getWorkspaceRepository(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });

  const index = useQuery({
    queryKey: queryKeys.vaultIndex(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before checking its Vault index.");
      }
      return client.getVaultIndex(activeWorkspaceId);
    },
    enabled: activeWorkspaceId !== null,
    retry: false,
  });

  const inventory = useQuery({
    queryKey: queryKeys.vaultInventory(activeWorkspaceId ?? "none"),
    queryFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before loading its file tree.");
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
        throw new Error("Select a workspace before listing its files.");
      }
      return client.listVaultFiles(activeWorkspaceId, { limit: FILE_LIMIT });
    },
    enabled: activeWorkspaceId !== null && inventory.isSuccess,
    retry: false,
  });

  const build = useMutation({
    mutationFn: () => {
      if (!activeWorkspaceId) {
        throw new Error("Select a workspace before building its inventory.");
      }
      return client.buildVaultInventory(activeWorkspaceId);
    },
    onSuccess: (snapshot) => {
      queryClient.setQueryData(queryKeys.vaultInventory(snapshot.workspaceId), snapshot);
      queryClient.removeQueries({
        queryKey: ["core", "workspaces", snapshot.workspaceId, "vault", "files", "content"],
      });
      void queryClient.invalidateQueries({
        queryKey: queryKeys.vaultFiles(snapshot.workspaceId),
      });
    },
  });

  const tree = useMemo(
    () => buildFileTree(files.data?.items ?? []),
    [files.data],
  );

  const selectedFile = useMemo<VaultFileInventoryItem | null>(
    () => files.data?.items.find((item) => item.path === selectedPath) ?? null,
    [files.data, selectedPath],
  );

  // Apply a cross-panel open request (Vault → Workspace). Keyed on the request
  // nonce so re-opening the same path — or a new line range — re-triggers.
  useEffect(() => {
    if (!openRequest) return;
    setSelectedPath(openRequest.path);
    setRevealPath(openRequest.path);
    setHighlight(
      openRequest.startLine !== undefined && openRequest.endLine !== undefined
        ? { startLine: openRequest.startLine, endLine: openRequest.endLine }
        : null,
    );
    containerRef.current?.scrollIntoView?.({ behavior: "smooth", block: "start" });
    // Intentionally keyed only on the request nonce: re-running on `openRequest`
    // identity would re-apply on unrelated re-renders.
  }, [openRequest?.requestId]);

  const handleSelectFile = (file: VaultFileInventoryItem) => {
    setSelectedPath(file.path);
    setHighlight(null);
    setRevealPath(null);
  };

  const notBuilt = inventory.isError && isProblem(inventory.error, INVENTORY_NOT_BUILT_TYPE);

  return (
    <div ref={containerRef} className="workspace-anchor">
      <Panel
        eyebrow="Repository, editor & tasks"
        title="Workspace"
        toolbar={
          activeWorkspaceId && !inventory.isPending ? (
            <button
              className="button button--primary"
              type="button"
              onClick={() => build.mutate()}
              disabled={build.isPending}
            >
              {build.isPending
                ? "Building…"
                : inventory.isSuccess
                  ? "Refresh files"
                  : "Build file tree"}
            </button>
          ) : undefined
        }
      >
        {!activeWorkspaceId ? (
          <EmptyState>
            Open a workspace to browse its repository, view files, and see its task board.
          </EmptyState>
        ) : (
          <>
            <WorkspaceStatusBar repository={repository} index={index} />

            {inventory.isPending ? (
              <LoadingState>Loading the repository file tree…</LoadingState>
            ) : null}

            {notBuilt ? (
              <>
                <EmptyState>
                  Build the workspace file tree to browse the repository and open files in the
                  editor.
                </EmptyState>
                {selectedPath ? (
                  <p className="workspace-editor__note" role="status">
                    Vault asked to open <code>{selectedPath}</code>. Build the file tree to view it.
                  </p>
                ) : null}
              </>
            ) : null}

            {inventory.isError && !notBuilt ? (
              <ProblemDetailsView error={inventory.error} />
            ) : null}

            {build.isError ? <ProblemDetailsView error={build.error} /> : null}

            {inventory.isSuccess ? (
              <div className="workspace-body">
                <aside className="workspace-tree-pane" aria-label="Repository tree">
                  <div className="workspace-section-heading">
                    <strong>Files</strong>
                    {files.isSuccess ? (
                      <span>
                        {files.data.returned} of {files.data.total}
                      </span>
                    ) : null}
                  </div>
                  {files.isPending ? <LoadingState>Loading files…</LoadingState> : null}
                  {files.isError ? <ProblemDetailsView error={files.error} /> : null}
                  {files.isSuccess && files.data.items.length === 0 ? (
                    <EmptyState>No files were inventoried for this workspace.</EmptyState>
                  ) : null}
                  {files.isSuccess && files.data.items.length > 0 ? (
                    <div className="workspace-tree-scroll">
                      <RepositoryTree
                        nodes={tree}
                        selectedPath={selectedPath}
                        onSelectFile={handleSelectFile}
                        revealPath={revealPath}
                      />
                    </div>
                  ) : null}
                  {files.isSuccess && files.data.total > files.data.returned ? (
                    <p className="workspace-hint">
                      Showing the first {files.data.returned} files. Larger repositories are
                      truncated for the tree.
                    </p>
                  ) : null}
                </aside>

                <div className="workspace-editor-pane" aria-label="File editor">
                  <WorkspaceEditor
                    workspaceId={activeWorkspaceId}
                    path={selectedPath}
                    file={selectedFile}
                    highlight={highlight}
                  />
                </div>
              </div>
            ) : null}

            <TaskBoardPanel workspaceId={activeWorkspaceId} />
          </>
        )}
      </Panel>
    </div>
  );
}

function WorkspaceStatusBar({
  repository,
  index,
}: {
  repository: UseQueryResult<RepositorySummary, Error>;
  index: UseQueryResult<VaultIndexSnapshot, Error>;
}) {
  return (
    <div className="workspace-status" aria-label="Workspace status">
      <RepositoryStatus repository={repository} />
      <IndexStatus index={index} />
    </div>
  );
}

function RepositoryStatus({
  repository,
}: {
  repository: UseQueryResult<RepositorySummary, Error>;
}) {
  if (repository.isPending) {
    return <span className="workspace-status__muted">Checking repository…</span>;
  }
  if (repository.isSuccess) {
    const summary = repository.data;
    return (
      <span className="workspace-status__repo">
        <span className="badge">Git</span>
        {summary.branch ? <code>{summary.branch}</code> : null}
        <span className={summary.isDirty ? "badge badge--dirty" : "badge badge--clean"}>
          {summary.isDirty ? "uncommitted changes" : "clean"}
        </span>
      </span>
    );
  }
  if (isProblem(repository.error, NOT_A_GIT_REPOSITORY_TYPE)) {
    return (
      <span className="workspace-status__muted">
        Not a Git repository — connect one to enable repository features.
      </span>
    );
  }
  return <span className="workspace-status__muted">Repository status unavailable.</span>;
}

function IndexStatus({
  index,
}: {
  index: UseQueryResult<VaultIndexSnapshot, Error>;
}) {
  if (index.isSuccess) {
    return (
      <span className="workspace-status__index" title="This workspace is indexed in Vault memory.">
        <span className="badge badge--clean">Indexed by Vault</span>
      </span>
    );
  }
  if (index.isError && isProblem(index.error, INDEX_NOT_BUILT_TYPE)) {
    return (
      <span className="workspace-status__muted">
        Not indexed by Vault — index it from the Vault memory panel.
      </span>
    );
  }
  return null;
}

function isProblem(error: unknown, type: string): boolean {
  return error instanceof CoreApiError && error.problem.type === type;
}
