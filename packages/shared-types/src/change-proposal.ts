import type { ContextPackDigest } from "./context-pack.js";
import type { IsoDateTime } from "./domain.js";
import type { PromptVersion, ProviderId } from "./provider.js";

export const CHANGE_PROPOSAL_SCHEMA_VERSION = "1" as const;
export const CHANGE_PROPOSAL_STATUSES = [
  "proposed",
  "approved",
  "rejected",
] as const;
export const CHANGE_PROPOSAL_CHANGE_TYPES = [
  "create",
  "modify",
  "delete",
] as const;

export const CHANGE_PROPOSAL_LIMITS = {
  maxFileChanges: 16,
  maxSourceTextBytes: 131_072,
  maxStoredTextBytesPerFile: 8_192,
  maxStoredTextBytesTotal: 32_768,
} as const;

export type ChangeProposalStatus = (typeof CHANGE_PROPOSAL_STATUSES)[number];
export type ChangeProposalChangeType =
  (typeof CHANGE_PROPOSAL_CHANGE_TYPES)[number];

/** Immutable provider output captured on a successful run before review state exists. */
export interface ChangeProposalDraftFileChange {
  path: string;
  changeType: ChangeProposalChangeType;
  language: string | null;
  proposedText: string | null;
}

export interface ChangeProposalDraft {
  summary: string;
  rationale: string;
  fileChanges: readonly ChangeProposalDraftFileChange[];
}

export interface ChangeProposalFileChange {
  path: string;
  changeType: ChangeProposalChangeType;
  language: string | null;
  beforeDigest: ContextPackDigest | null;
  afterDigest: ContextPackDigest | null;
  proposedText: string | null;
  proposedTextBytes: number;
  originalTextBytes: number;
  truncated: boolean;
}

export interface ChangeProposal {
  id: string;
  schemaVersion: typeof CHANGE_PROPOSAL_SCHEMA_VERSION;
  runId: string;
  taskId: string;
  workspaceId: string;
  contextPackId: ContextPackDigest;
  providerId: ProviderId;
  promptVersion: PromptVersion;
  status: ChangeProposalStatus;
  createdAt: IsoDateTime;
  reviewedAt: IsoDateTime | null;
  summary: string;
  rationale: string;
  fileChanges: readonly ChangeProposalFileChange[];
}

export interface CreateChangeProposalResponse {
  proposal: ChangeProposal;
  created: boolean;
}

export interface ChangeProposalCollection {
  items: readonly ChangeProposal[];
  total: number;
}
