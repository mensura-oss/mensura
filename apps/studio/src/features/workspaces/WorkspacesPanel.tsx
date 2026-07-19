import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import { EmptyState, LoadingState } from "../../components/AsyncState";
import { Panel } from "../../components/Panel";
import { ProblemDetailsView } from "../../components/ProblemDetailsView";
import { formatTimestamp } from "../../components/ResourceDetails";

export function WorkspacesPanel() {
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
    onSuccess: async () => {
      setName("");
      setRootPath("");
      await queryClient.invalidateQueries({ queryKey: queryKeys.workspaces });
    },
  });

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
          <ul className="workspace-cards">
            {workspaces.data.items.map((workspace) => (
              <li key={workspace.id}>
                <div>
                  <strong>{workspace.name}</strong>
                  <code>{workspace.rootPath}</code>
                </div>
                <time dateTime={workspace.createdAt}>
                  {formatTimestamp(workspace.createdAt)}
                </time>
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </Panel>
  );
}
