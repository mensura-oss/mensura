import { describe, expect, it } from "vitest";

import {
  RUN_EXECUTION_SCHEMA_VERSION,
  RUN_STATUSES,
  type RunExecution,
} from "./index.js";

describe("run execution v1 contracts", () => {
  it("pins the first real run state machine", () => {
    expect(RUN_STATUSES).toEqual(["queued", "running", "succeeded", "failed"]);
  });

  it("keeps provider identity and bounded terminal output explicit", () => {
    const execution: RunExecution = {
      provider: {
        providerId: "mensura.builtin",
        adapterId: "deterministic-review",
        adapterVersion: "1.0.0",
        model: null,
      },
      durationMs: 4,
      result: {
        schemaVersion: RUN_EXECUTION_SCHEMA_VERSION,
        taskSummary: "Inspect the selected context.",
        interpretedIntent: "Review",
        context: {
          contextPackId: `sha256:${"a".repeat(64)}`,
          inventoryId: "inventory-id",
          fileCount: 2,
          textFileCount: 2,
          binaryFileCount: 0,
          totalFileBytes: 1024,
          totalPreviewBytes: 512,
          truncatedTextFileCount: 0,
          languages: ["Python"],
        },
        warnings: [],
        recommendedNextSteps: ["Review the result."],
      },
      failure: null,
    };

    expect(execution.result?.schemaVersion).toBe("1");
    expect(execution.provider.model).toBeNull();
  });
});
