import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useRef, useState } from "react";
import { useCoreClient } from "../api/CoreClientProvider";
import { BackupPanel } from "../features/backup/BackupPanel";
import { ContextPackPanel } from "../features/context-packs/ContextPackPanel";
import { useLiveEvents } from "../features/events/useLiveEvents";
import { HealthPanel } from "../features/health/HealthPanel";
import { GuardPanel } from "../features/guard/GuardPanel";
import { JobsPanel } from "../features/jobs/JobsPanel";
import { RunInspector } from "../features/runs/RunInspector";
import { RepositorySummaryPanel } from "../features/repository/RepositorySummaryPanel";
import { ProviderSettingsPanel } from "../features/providers/ProviderSettingsPanel";
import { TaskInspector } from "../features/tasks/TaskInspector";
import { TaskCreationPanel } from "../features/tasks/TaskCreationPanel";
import { VaultIndexPanel } from "../features/vault/VaultIndexPanel";
import { VaultPanel } from "../features/vault/VaultPanel";
import { WorkspacePanel } from "../features/workspace/WorkspacePanel";
import type { WorkspaceOpenRequest } from "../features/workspace/types";
import { WorkspacesPanel } from "../features/workspaces/WorkspacesPanel";
import { AppShell } from "../layout/AppShell";
import { useActiveWorkspaceId } from "./useActiveWorkspaceId";

export function App() {
  const client = useCoreClient();
  const [activeWorkspaceId, setActiveWorkspaceId] = useActiveWorkspaceId();
  const queryClient = useQueryClient();

  // A file-open request routed from Vault into the Workspace editor. The nonce
  // ref makes each request distinct so re-opening the same path re-triggers.
  const openRequestNonce = useRef(0);
  const [workspaceOpen, setWorkspaceOpen] = useState<WorkspaceOpenRequest | null>(
    null,
  );

  const openInWorkspace = useCallback(
    (request: { path: string; startLine?: number; endLine?: number }) => {
      openRequestNonce.current += 1;
      setWorkspaceOpen({ requestId: openRequestNonce.current, ...request });
    },
    [],
  );

  const handleActiveWorkspaceChange = useCallback(
    (workspaceId: string | null) => {
      // A different workspace has its own repository and files; drop any pending
      // cross-panel open request so it can't apply to the wrong workspace.
      setWorkspaceOpen(null);
      setActiveWorkspaceId(workspaceId);
    },
    [setActiveWorkspaceId],
  );

  useLiveEvents({ workspaceId: activeWorkspaceId, queryClient });

  return (
    <AppShell baseUrl={client.baseUrl}>
      <div className="dashboard-grid">
        <div className="dashboard-grid__status">
          <HealthPanel />
        </div>
        <div className="dashboard-grid__providers">
          <ProviderSettingsPanel />
        </div>
        <div className="dashboard-grid__workspaces">
          <WorkspacesPanel
            activeWorkspaceId={activeWorkspaceId}
            onActiveWorkspaceChange={handleActiveWorkspaceChange}
          />
        </div>
        <div className="dashboard-grid__repository">
          <RepositorySummaryPanel activeWorkspaceId={activeWorkspaceId} />
        </div>
        <div className="dashboard-grid__workspace">
          <WorkspacePanel
            key={activeWorkspaceId ?? "no-workspace"}
            activeWorkspaceId={activeWorkspaceId}
            openRequest={workspaceOpen}
          />
        </div>
        <div className="dashboard-grid__guard">
          <GuardPanel
            key={activeWorkspaceId ?? "no-workspace"}
            activeWorkspaceId={activeWorkspaceId}
          />
        </div>
        <div className="dashboard-grid__vault">
          <VaultPanel
            key={activeWorkspaceId ?? "no-workspace"}
            activeWorkspaceId={activeWorkspaceId}
          />
        </div>
        <div className="dashboard-grid__vault-index">
          <VaultIndexPanel
            key={activeWorkspaceId ?? "no-workspace"}
            activeWorkspaceId={activeWorkspaceId}
            onOpenInWorkspace={openInWorkspace}
          />
        </div>
        <div className="dashboard-grid__context-packs">
          <ContextPackPanel
            key={activeWorkspaceId ?? "no-workspace"}
            activeWorkspaceId={activeWorkspaceId}
          />
        </div>
        <div className="dashboard-grid__task-flow">
          <TaskCreationPanel
            key={activeWorkspaceId ?? "no-workspace"}
            activeWorkspaceId={activeWorkspaceId}
          />
        </div>
        <TaskInspector />
        <RunInspector />
        <div className="dashboard-grid__backup">
          <BackupPanel />
        </div>
        <div className="dashboard-grid__jobs">
          <JobsPanel />
        </div>
      </div>
    </AppShell>
  );
}
