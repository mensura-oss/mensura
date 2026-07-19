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
  it("allows only explicit execution transitions", () => {
    expect(canTransitionRun("queued", "running")).toBe(true);
    expect(canTransitionRun("running", "succeeded")).toBe(true);
    expect(canTransitionRun("running", "failed")).toBe(true);
    expect(canTransitionRun("queued", "succeeded")).toBe(false);
    expect(canTransitionRun("succeeded", "running")).toBe(false);
  });

  it("treats succeeded and failed runs as terminal", () => {
    expect(isTerminalRunStatus("succeeded")).toBe(true);
    expect(isTerminalRunStatus("failed")).toBe(true);
    expect(isTerminalRunStatus("queued")).toBe(false);
    expect(isTerminalRunStatus("running")).toBe(false);
  });
});
