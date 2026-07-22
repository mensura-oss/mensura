/**
 * A request from elsewhere in Studio (today: a Vault search hit) to open a file
 * in the Workspace editor. `requestId` is a monotonically increasing nonce so
 * re-opening the same path — or the same path at a different line range —
 * re-triggers the open effect even when the path is unchanged.
 */
export interface WorkspaceOpenRequest {
  requestId: number;
  path: string;
  startLine?: number;
  endLine?: number;
}

/**
 * Callback other panels use to open a file in the Workspace editor. `App` owns
 * the implementation (it stamps a {@link WorkspaceOpenRequest} nonce); callers
 * only supply the target path and optional line range.
 */
export type OpenInWorkspaceHandler = (request: {
  path: string;
  startLine?: number;
  endLine?: number;
}) => void;
