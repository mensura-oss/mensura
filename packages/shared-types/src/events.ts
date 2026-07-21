import type { EntityId, IsoDateTime, RunStatus } from "./domain.js";
import type { BackupStatus } from "./backup.js";
import type { UndoStatus } from "./undo.js";

export const EVENT_SCHEMA_VERSION = "1" as const;

export const EVENT_TYPES = [
  "run.status.changed",
  "verification.created",
  "application.created",
  "undo.created",
  "backup.created",
  "job.status.changed",
] as const;
export type EventType = (typeof EVENT_TYPES)[number];

export type EventEntityType =
  | "run"
  | "verification"
  | "application"
  | "undo"
  | "backup"
  | "job";

export interface MensuraEvent {
  eventId: EntityId;
  eventType: EventType;
  occurredAt: IsoDateTime;
  workspaceId?: EntityId;
  entityType: EventEntityType;
  entityId: EntityId;
  status: string;
  summary: string;
}

export interface SseConnectedEvent {
  eventType: "connected";
  bufferSize: number;
}
