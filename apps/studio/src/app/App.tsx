import { useCoreClient } from "../api/CoreClientProvider";
import { HealthPanel } from "../features/health/HealthPanel";
import { RunInspector } from "../features/runs/RunInspector";
import { TaskInspector } from "../features/tasks/TaskInspector";
import { WorkspacesPanel } from "../features/workspaces/WorkspacesPanel";
import { AppShell } from "../layout/AppShell";

export function App() {
  const client = useCoreClient();

  return (
    <AppShell baseUrl={client.baseUrl}>
      <div className="dashboard-grid">
        <div className="dashboard-grid__status">
          <HealthPanel />
        </div>
        <div className="dashboard-grid__workspaces">
          <WorkspacesPanel />
        </div>
        <TaskInspector />
        <RunInspector />
      </div>
    </AppShell>
  );
}
