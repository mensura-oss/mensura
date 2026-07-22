import { QueryClient } from "@tanstack/react-query";
import { act, renderHook } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { CoreClientProvider } from "../../api/CoreClientProvider";
import { queryKeys } from "../../app/queryClient";
import {
  FakeEventSource,
  installFakeEventSource,
} from "../../test/fakeEventSource";
import { createTestClient } from "../../test/render";
import { useLiveEvents } from "./useLiveEvents";

const activeWorkspaceId = "5ca252af-76f4-4aed-9718-ff97b610ce90";
const otherWorkspaceId = "11111111-2222-3333-4444-555555555555";

function runStatusEvent(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    eventId: "e1",
    eventType: "run.status.changed",
    occurredAt: "2026-07-22T12:00:00Z",
    workspaceId: activeWorkspaceId,
    entityType: "run",
    entityId: "run-1",
    status: "succeeded",
    summary: "Run succeeded.",
    ...overrides,
  };
}

function renderLiveEvents(workspaceId: string) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const invalidateQueries = vi.spyOn(queryClient, "invalidateQueries");
  const client = createTestClient();
  const wrapper = ({ children }: { children: ReactNode }) => (
    <CoreClientProvider client={client}>{children}</CoreClientProvider>
  );
  const view = renderHook(() => useLiveEvents({ workspaceId, queryClient }), {
    wrapper,
  });
  return { queryClient, invalidateQueries, ...view };
}

describe("useLiveEvents", () => {
  let restoreEventSource: () => void;

  beforeEach(() => {
    restoreEventSource = installFakeEventSource();
  });

  afterEach(() => {
    restoreEventSource();
    vi.restoreAllMocks();
  });

  it("subscribes to the workspace-filtered Core event stream", () => {
    renderLiveEvents(activeWorkspaceId);
    expect(FakeEventSource.latest().url).toBe(
      `http://127.0.0.1:8000/api/v1/events/stream?workspaceId=${activeWorkspaceId}`,
    );
  });

  it("refetches the workspace task board when a run status event arrives", () => {
    const { invalidateQueries } = renderLiveEvents(activeWorkspaceId);

    act(() => {
      FakeEventSource.latest().emit("run.status.changed", runStatusEvent());
    });

    // The single run detail is refreshed, and — the fix under test — so is the
    // board's workspace task list, so its latestRun badge updates in place.
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: queryKeys.run("run-1"),
    });
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: queryKeys.workspaceTasks(activeWorkspaceId),
    });
  });

  it("never invalidates the active board for an unrelated workspace's run event", () => {
    const { invalidateQueries } = renderLiveEvents(activeWorkspaceId);

    act(() => {
      FakeEventSource.latest().emit(
        "run.status.changed",
        runStatusEvent({ workspaceId: otherWorkspaceId, entityId: "run-2" }),
      );
    });

    // The invalidation is keyed by the event's own workspace, so an unrelated
    // workspace's board is never marked stale — no churn on the active board.
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: queryKeys.workspaceTasks(otherWorkspaceId),
    });
    expect(invalidateQueries).not.toHaveBeenCalledWith({
      queryKey: queryKeys.workspaceTasks(activeWorkspaceId),
    });
  });

  it("skips the board invalidation when a run event carries no workspace", () => {
    const { invalidateQueries } = renderLiveEvents(activeWorkspaceId);

    act(() => {
      FakeEventSource.latest().emit(
        "run.status.changed",
        runStatusEvent({ workspaceId: undefined }),
      );
    });

    // Only the run detail can be scoped; there is no workspace to refetch a
    // board for, so exactly one invalidation is issued.
    expect(invalidateQueries).toHaveBeenCalledTimes(1);
    expect(invalidateQueries).toHaveBeenCalledWith({
      queryKey: queryKeys.run("run-1"),
    });
  });

  it("closes the event stream on unmount so it can cleanly reconnect", () => {
    const { unmount } = renderLiveEvents(activeWorkspaceId);
    const source = FakeEventSource.latest();

    expect(source.closed).toBe(false);
    unmount();
    expect(source.closed).toBe(true);
  });
});
