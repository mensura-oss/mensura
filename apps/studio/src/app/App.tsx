import { useCoreClient } from "../api/CoreClientProvider";
import { ContextPackPanel } from "../features/context-packs/ContextPackPanel";
import { HealthPanel } from "../features/health/HealthPanel";
import { GuardPanel } from "../features/guard/GuardPanel";
import { RunInspector } from "../features/runs/RunInspector";
import { RepositorySummaryPanel } from "../features/repository/RepositorySummaryPanel";
import { ProviderSettingsPanel } from "../features/providers/ProviderSettingsPanel";
import { TaskInspector } from "../features/tasks/TaskInspector";
import { TaskCreationPanel } from "../features/tasks/TaskCreationPanel";
import { VaultPanel } from "../features/vault/VaultPanel";
import { WorkspacesPanel } from "../features/workspaces/WorkspacesPanel";
import { AppShell } from "../layout/AppShell";
import { useActiveWorkspaceId } from "./useActiveWorkspaceId";

export function App() {
  const client = useCoreClient();
  const [activeWorkspaceId, setActiveWorkspaceId] = useActiveWorkspaceId();

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
            onActiveWorkspaceChange={setActiveWorkspaceId}
          />
        </div>
        <div className="dashboard-grid__repository">
          <RepositorySummaryPanel activeWorkspaceId={activeWorkspaceId} />
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
      </div>
    </AppShell>
  );
}
