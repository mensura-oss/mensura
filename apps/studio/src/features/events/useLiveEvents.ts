import { useEffect, useRef } from "react";
import type { QueryClient } from "@tanstack/react-query";
import type { MensuraEvent } from "@mensura/shared-types";
import { useCoreClient } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";

interface UseLiveEventsOptions {
  workspaceId: string | null;
  queryClient: QueryClient;
}

export function useLiveEvents({ workspaceId, queryClient }: UseLiveEventsOptions) {
  const client = useCoreClient();
  const queryClientRef = useRef(queryClient);
  queryClientRef.current = queryClient;

  useEffect(() => {
    // EventSource is unavailable in non-browser environments (SSR, jsdom tests).
    // Live updates are a progressive enhancement; REST remains the source of truth.
    if (typeof EventSource === "undefined") {
      return;
    }

    const url = new URL(`${client.baseUrl}/api/v1/events/stream`);
    if (workspaceId) {
      url.searchParams.set("workspaceId", workspaceId);
    }

    const es = new EventSource(url.toString());

    const handleEvent = (event: MessageEvent) => {
      if (event.type === "connected") return;

      let parsed: MensuraEvent;
      try {
        parsed = JSON.parse(event.data);
      } catch {
        return;
      }

      const qc = queryClientRef.current;
      switch (parsed.eventType) {
        case "run.status.changed":
          qc.invalidateQueries({ queryKey: queryKeys.run(parsed.entityId) });
          // Keep the Workspace task board live: a run reaching a terminal state
          // changes its task's compact `latestRun`, so refetch that workspace's
          // task list. Scoped by the event's own `workspaceId` (and the stream
          // is already workspace-filtered), and `invalidateQueries` only refetches
          // mounted queries, so an unrelated workspace's board never churns.
          if (parsed.workspaceId) {
            qc.invalidateQueries({
              queryKey: queryKeys.workspaceTasks(parsed.workspaceId),
            });
          }
          break;
        case "verification.created":
          qc.invalidateQueries({ queryKey: queryKeys.verification(parsed.entityId) });
          if (parsed.workspaceId) {
            qc.invalidateQueries({
              queryKey: queryKeys.changeProposals(parsed.workspaceId),
            });
          }
          break;
        case "application.created":
          qc.invalidateQueries({ queryKey: queryKeys.application(parsed.entityId) });
          if (parsed.workspaceId) {
            qc.invalidateQueries({
              queryKey: queryKeys.workspaceApplications(parsed.workspaceId),
            });
          }
          break;
        case "undo.created":
          qc.invalidateQueries({ queryKey: queryKeys.undo(parsed.entityId) });
          if (parsed.workspaceId) {
            qc.invalidateQueries({
              queryKey: queryKeys.workspaceUndos(parsed.workspaceId),
            });
          }
          break;
        case "backup.created":
          qc.invalidateQueries({ queryKey: queryKeys.backups });
          break;
        case "job.status.changed":
          qc.invalidateQueries({ queryKey: queryKeys.jobs });
          qc.invalidateQueries({ queryKey: queryKeys.job(parsed.entityId) });
          break;
      }
    };

    es.addEventListener("run.status.changed", handleEvent);
    es.addEventListener("verification.created", handleEvent);
    es.addEventListener("application.created", handleEvent);
    es.addEventListener("undo.created", handleEvent);
    es.addEventListener("backup.created", handleEvent);
    es.addEventListener("job.status.changed", handleEvent);

    return () => {
      es.removeEventListener("run.status.changed", handleEvent);
      es.removeEventListener("verification.created", handleEvent);
      es.removeEventListener("application.created", handleEvent);
      es.removeEventListener("undo.created", handleEvent);
      es.removeEventListener("backup.created", handleEvent);
      es.removeEventListener("job.status.changed", handleEvent);
      es.close();
    };
  }, [client.baseUrl, workspaceId]);
}
