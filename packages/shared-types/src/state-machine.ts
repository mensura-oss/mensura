import type { RunStatus, TaskStatus } from "./domain.js";

const taskTransitions = {
  draft: ["ready", "cancelled"],
  ready: ["running", "cancelled"],
  running: ["review", "failed", "cancelled"],
  review: ["approved", "rejected", "running", "cancelled"],
  approved: [],
  rejected: ["running", "cancelled"],
  failed: ["ready", "cancelled"],
  cancelled: [],
} as const satisfies Record<TaskStatus, readonly TaskStatus[]>;

const runTransitions = {
  queued: ["running"],
  running: ["succeeded", "failed"],
  succeeded: [],
  failed: [],
} as const satisfies Record<RunStatus, readonly RunStatus[]>;

export function canTransitionTask(from: TaskStatus, to: TaskStatus): boolean {
  return (taskTransitions[from] as readonly TaskStatus[]).includes(to);
}

export function canTransitionRun(from: RunStatus, to: RunStatus): boolean {
  return (runTransitions[from] as readonly RunStatus[]).includes(to);
}

export function isTerminalTaskStatus(status: TaskStatus): boolean {
  return taskTransitions[status].length === 0;
}

export function isTerminalRunStatus(status: RunStatus): boolean {
  return runTransitions[status].length === 0;
}
