import { describe, expect, it } from "vitest";

import {
  GUARD_CHECK_KINDS,
  GUARD_CHECK_STATUSES,
  GUARD_RUN_STATUSES,
} from "./guard.js";

describe("Guard v1 contract vocabulary", () => {
  it("limits the MVP to lint and test checks", () => {
    expect(GUARD_CHECK_KINDS).toEqual(["lint", "test"]);
  });

  it("keeps check errors distinct from completed failures", () => {
    expect(GUARD_CHECK_STATUSES).toEqual(["passed", "failed", "error"]);
    expect(GUARD_RUN_STATUSES).toEqual(["passed", "failed"]);
  });
});
