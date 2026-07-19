import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";

import {
  ACTIVE_WORKSPACE_STORAGE_KEY,
  useActiveWorkspaceId,
} from "./useActiveWorkspaceId";

describe("useActiveWorkspaceId", () => {
  beforeEach(() => {
    window.localStorage.clear();
  });

  it("restores and updates the active workspace selection", () => {
    window.localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, "workspace-one");
    const { result } = renderHook(() => useActiveWorkspaceId());

    expect(result.current[0]).toBe("workspace-one");

    act(() => result.current[1]("workspace-two"));
    expect(result.current[0]).toBe("workspace-two");
    expect(window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY)).toBe(
      "workspace-two",
    );

    act(() => result.current[1](null));
    expect(result.current[0]).toBeNull();
    expect(window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY)).toBeNull();
  });
});
