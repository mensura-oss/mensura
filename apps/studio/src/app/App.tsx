import { useCoreClient } from "../api/CoreClientProvider";
import { HealthPanel } from "../features/health/HealthPanel";
import { RunInspector } from "../features/runs/RunInspector";
import { TaskInspector } from "../features/tasks/TaskInspector";
import { TaskCreationPanel } from "../features/tasks/TaskCreationPanel";
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
        <div className="dashboard-grid__workspaces">
          <WorkspacesPanel
            activeWorkspaceId={activeWorkspaceId}
            onActiveWorkspaceChange={setActiveWorkspaceId}
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
