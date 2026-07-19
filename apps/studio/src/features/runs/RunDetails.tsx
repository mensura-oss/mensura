import type { Run } from "@mensura/shared-types";

import {
  formatTimestamp,
  ResourceDetails,
} from "../../components/ResourceDetails";
import { RunExecutionPanel } from "./RunExecutionPanel";

export function RunDetails({ run }: { run: Run }) {
  return (
    <div className="run-details">
      <ResourceDetails
        items={[
        { label: "ID", value: <code>{run.id}</code> },
        { label: "Task", value: <code>{run.taskId}</code> },
        {
          label: "Immutable context pack",
          value: <code>{run.contextPackId}</code>,
        },
        {
          label: "Context workspace",
          value: <code>{run.contextPack.workspaceId}</code>,
        },
        {
          label: "Vault inventory",
          value: <code>{run.contextPack.inventoryId}</code>,
        },
        {
          label: "Context schema",
          value: run.contextPack.schemaVersion,
        },
        {
          label: "Context files",
          value: run.contextPack.fileCount.toLocaleString(),
        },
        {
          label: "Context file bytes",
          value: run.contextPack.totalFileBytes.toLocaleString(),
        },
        {
          label: "Captured preview bytes",
          value: run.contextPack.totalPreviewBytes.toLocaleString(),
        },
        {
          label: "Status",
          value: (
            <span className={`badge badge--${run.status}`}>{run.status}</span>
          ),
        },
        { label: "Started", value: formatTimestamp(run.startedAt) },
        { label: "Finished", value: formatTimestamp(run.finishedAt) },
        { label: "Created", value: formatTimestamp(run.createdAt) },
        { label: "Updated", value: formatTimestamp(run.updatedAt) },
        ]}
      />
      <RunExecutionPanel key={run.id} run={run} />
    </div>
  );
}
