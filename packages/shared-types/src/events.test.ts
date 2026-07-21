import { describe, expect, it } from "vitest";
import type { MensuraEvent, SseConnectedEvent } from "./events.js";

describe("MensuraEvent", () => {
  const validEvent: MensuraEvent = {
    eventId: "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    eventType: "run.status.changed",
    occurredAt: "2026-07-20T12:00:00Z",
    workspaceId: "ws-123",
    entityType: "run",
    entityId: "run-456",
    status: "succeeded",
    summary: "Run completed successfully",
  };

  it("accepts a valid event", () => {
    expect(validEvent.eventType).toBe("run.status.changed");
    expect(validEvent.entityType).toBe("run");
  });

  it("does not require workspaceId", () => {
    const ev: MensuraEvent = {
      ...validEvent,
      workspaceId: undefined,
    };
    expect(ev.workspaceId).toBeUndefined();
  });

  it("supports all defined event types", () => {
    const types = [
      "run.status.changed",
      "verification.created",
      "application.created",
      "undo.created",
      "backup.created",
    ] as const;
    for (const t of types) {
      const ev: MensuraEvent = { ...validEvent, eventType: t };
      expect(ev.eventType).toBe(t);
    }
  });

  it("connects with bounded payload", () => {
    const ev: MensuraEvent = {
      eventId: "ev-1",
      eventType: "application.created",
      occurredAt: "2026-07-20T12:00:00Z",
      workspaceId: "ws-1",
      entityType: "application",
      entityId: "app-1",
      status: "applied_guard_passed",
      summary: "Application completed. Guard: passed.",
    };
    expect(ev.summary.length).toBeLessThan(200);
  });
});

describe("SseConnectedEvent", () => {
  it("has connected type and buffer size", () => {
    const ev: SseConnectedEvent = {
      eventType: "connected",
      bufferSize: 0,
    };
    expect(ev.eventType).toBe("connected");
  });
});
