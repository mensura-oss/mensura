import { useCallback, useState } from "react";

export const ACTIVE_WORKSPACE_STORAGE_KEY = "mensura:active-workspace-id";

function readStoredWorkspaceId() {
  try {
    return window.localStorage.getItem(ACTIVE_WORKSPACE_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function useActiveWorkspaceId() {
  const [activeWorkspaceId, setActiveWorkspaceIdState] = useState<string | null>(
    readStoredWorkspaceId,
  );

  const setActiveWorkspaceId = useCallback((workspaceId: string | null) => {
    setActiveWorkspaceIdState(workspaceId);
    try {
      if (workspaceId) {
        window.localStorage.setItem(ACTIVE_WORKSPACE_STORAGE_KEY, workspaceId);
      } else {
        window.localStorage.removeItem(ACTIVE_WORKSPACE_STORAGE_KEY);
      }
    } catch {
      // Selection still works for this session when storage is unavailable.
    }
  }, []);

  return [activeWorkspaceId, setActiveWorkspaceId] as const;
}
