import { describe, expect, it } from "vitest";

import {
  canTransitionRun,
  canTransitionTask,
  isTerminalRunStatus,
  isTerminalTaskStatus,
} from "./state-machine.js";

describe("task lifecycle", () => {
  it("allows the normal review and approval path", () => {
    expect(canTransitionTask("draft", "ready")).toBe(true);
    expect(canTransitionTask("ready", "running")).toBe(true);
    expect(canTransitionTask("running", "review")).toBe(true);
    expect(canTransitionTask("review", "approved")).toBe(true);
  });

  it("blocks skipping review", () => {
    expect(canTransitionTask("running", "approved")).toBe(false);
  });

  it("marks only states without outgoing transitions as terminal", () => {
    expect(isTerminalTaskStatus("approved")).toBe(true);
    expect(isTerminalTaskStatus("cancelled")).toBe(true);
    expect(isTerminalTaskStatus("failed")).toBe(false);
  });
});

describe("run lifecycle", () => {
  it("requires checks and approval before completion", () => {
    expect(canTransitionRun("executing", "checking")).toBe(true);
    expect(canTransitionRun("checking", "awaiting_approval")).toBe(true);
    expect(canTransitionRun("awaiting_approval", "completed")).toBe(true);
    expect(canTransitionRun("executing", "completed")).toBe(false);
  });

  it("supports revision from the approval checkpoint", () => {
    expect(canTransitionRun("awaiting_approval", "executing")).toBe(true);
  });

  it("treats completed, failed, and cancelled runs as terminal", () => {
    expect(isTerminalRunStatus("completed")).toBe(true);
    expect(isTerminalRunStatus("failed")).toBe(true);
    expect(isTerminalRunStatus("cancelled")).toBe(true);
  });
});
