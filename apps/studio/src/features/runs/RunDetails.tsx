import type { Run } from "@mensura/shared-types";

import {
  formatTimestamp,
  ResourceDetails,
} from "../../components/ResourceDetails";

export function RunDetails({ run }: { run: Run }) {
  return (
    <ResourceDetails
      items={[
        { label: "ID", value: <code>{run.id}</code> },
        { label: "Task", value: <code>{run.taskId}</code> },
        { label: "Status", value: <span className="badge">{run.status}</span> },
        { label: "Started", value: formatTimestamp(run.startedAt) },
        { label: "Finished", value: formatTimestamp(run.finishedAt) },
        { label: "Created", value: formatTimestamp(run.createdAt) },
        { label: "Updated", value: formatTimestamp(run.updatedAt) },
      ]}
    />
  );
}
