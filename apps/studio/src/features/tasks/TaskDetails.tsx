import type { Task } from "@mensura/shared-types";

import {
  formatTimestamp,
  ResourceDetails,
} from "../../components/ResourceDetails";
import { StartRunAction } from "../runs/StartRunAction";

export function TaskDetails({ task }: { task: Task }) {
  return (
    <div className="task-result">
      <ResourceDetails
        items={[
          { label: "ID", value: <code>{task.id}</code> },
          { label: "Workspace", value: <code>{task.workspaceId}</code> },
          { label: "Title", value: task.title },
          { label: "Description", value: task.description || "—" },
          { label: "Status", value: <span className="badge">{task.status}</span> },
          { label: "Assigned role", value: task.assignedRole ?? "—" },
          { label: "Created", value: formatTimestamp(task.createdAt) },
          { label: "Updated", value: formatTimestamp(task.updatedAt) },
        ]}
      />
      <StartRunAction
        key={task.id}
        taskId={task.id}
        workspaceId={task.workspaceId}
      />
    </div>
  );
}
