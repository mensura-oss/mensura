import type { WorkspaceCollection } from "@mensura/shared-types";
import { useEffect, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";

export function WorkspacesPanel({
  activeWorkspaceId,
  onActiveWorkspaceChange,
}: {
  activeWorkspaceId: string | null;
  onActiveWorkspaceChange(workspaceId: string | null): void;
}) {
  const client = useCoreClient();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [rootPath, setRootPath] = useState("");
  const workspaces = useQuery({
    queryKey: queryKeys.workspaces,
    queryFn: () => client.listWorkspaces(),
  });
  const createWorkspace = useMutation({
    mutationFn: () => client.createWorkspace({ name, rootPath }),
    onSuccess: (workspace) => {
      setName("");
      setRootPath("");
      queryClient.setQueryData<WorkspaceCollection>(
        queryKeys.workspaces,
        (current) => {
          if (!current) {
            return { items: [workspace], total: 1 };
          }
          if (current.items.some((item) => item.id === workspace.id)) {
            return current;
          }
          const items = [...current.items, workspace];
          return { items, total: items.length };
        },
      );
      onActiveWorkspaceChange(workspace.id);
      void queryClient.invalidateQueries({ queryKey: queryKeys.workspaces });
    },
  });

  useEffect(() => {
    if (
      workspaces.isSuccess &&
      activeWorkspaceId &&
      !workspaces.data.items.some((workspace) => workspace.id === activeWorkspaceId)
    ) {
      onActiveWorkspaceChange(null);
    }
  }, [
    activeWorkspaceId,
    onActiveWorkspaceChange,
    workspaces.data,
    workspaces.isSuccess,
  ]);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    createWorkspace.mutate();
  }

  return (
    <Panel eyebrow="Local roots" title="Workspaces">
      <form className="workspace-form" onSubmit={handleSubmit}>
        <label>
          <span>Name</span>
          <input
            name="workspace-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Mensura"
            maxLength={120}
            required
          />
        </label>
        <label className="workspace-form__path">
          <span>Root path</span>
          <input
            name="workspace-root"
            value={rootPath}
            onChange={(event) => setRootPath(event.target.value)}
            placeholder="/Users/me/projects/mensura"
            maxLength={4096}
            required
          />
        </label>
        <button
          className="button button--primary"
          type="submit"
          disabled={createWorkspace.isPending}
        >
          {createWorkspace.isPending ? "Creating…" : "Create workspace"}
        </button>
      </form>

      {createWorkspace.isError ? (
        <ProblemDetailsView error={createWorkspace.error} />
      ) : null}

      <div className="workspace-list" aria-live="polite">
        {workspaces.isPending ? (
          <LoadingState>Loading workspaces…</LoadingState>
        ) : null}
        {workspaces.isError ? (
          <ProblemDetailsView error={workspaces.error} />
        ) : null}
        {workspaces.isSuccess && workspaces.data.items.length === 0 ? (
          <EmptyState>
            No workspaces yet. Add a local root to establish the first Core state.
          </EmptyState>
        ) : null}
        {workspaces.isSuccess && workspaces.data.items.length > 0 ? (
          <>
            {!activeWorkspaceId ? (
              <EmptyState>Select a workspace to enable task creation.</EmptyState>
            ) : null}
            <ul className="workspace-cards">
              {workspaces.data.items.map((workspace) => {
                const isActive = workspace.id === activeWorkspaceId;
                return (
                  <li key={workspace.id}>
                    <button
                      className="workspace-card"
                      type="button"
                      aria-pressed={isActive}
                      onClick={() => onActiveWorkspaceChange(workspace.id)}
                    >
                      <div>
                        <span className="workspace-card__title">
                          <strong>{workspace.name}</strong>
                          {isActive ? <span className="badge">Active</span> : null}
                        </span>
                        <code>{workspace.rootPath}</code>
                      </div>
                      <time dateTime={workspace.createdAt}>
                        {formatTimestamp(workspace.createdAt)}
                      </time>
                    </button>
                  </li>
                );
              })}
            </ul>
          </>
        ) : null}
      </div>
    </Panel>
  );
}
