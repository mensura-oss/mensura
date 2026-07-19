import type { EntityId } from "./domain.js";

export const REPOSITORY_CHANGE_TYPES = [
  "added",
  "copied",
  "modified",
  "deleted",
  "renamed",
  "typeChanged",
  "unmerged",
  "untracked",
] as const;

export type RepositoryChangeType = (typeof REPOSITORY_CHANGE_TYPES)[number];

export interface RepositoryDiffMetadata {
  path: string;
  changeType: RepositoryChangeType;
  staged: boolean;
  oldPath?: string | null;
}

export interface RepositorySummary {
  workspaceId: EntityId;
  isRepository: true;
  branch: string | null;
  isDirty: boolean;
  stagedCount: number;
  unstagedCount: number;
  untrackedCount: number;
  changedPathsCount: number;
  diffMetadata: readonly RepositoryDiffMetadata[];
}
