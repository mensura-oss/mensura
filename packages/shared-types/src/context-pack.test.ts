import { describe, expect, it } from "vitest";

import {
  CONTEXT_PACK_CAPTURE_MODES,
  CONTEXT_PACK_SCHEMA_VERSION,
} from "./context-pack.js";

describe("context pack v1 contracts", () => {
  it("pins the canonical manifest schema version", () => {
    expect(CONTEXT_PACK_SCHEMA_VERSION).toBe("1");
  });

  it("makes captured text and metadata-only binary evidence explicit", () => {
    expect(CONTEXT_PACK_CAPTURE_MODES).toEqual(["text_preview", "metadata_only"]);
  });
});
