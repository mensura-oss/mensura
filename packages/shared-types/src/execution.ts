import type { ContextPackDigest } from "./context-pack.js";
import type { ChangeProposalDraft } from "./change-proposal.js";
import type { EntityId } from "./domain.js";
import type { PromptVersion, ProviderKind } from "./provider.js";

export const RUN_EXECUTION_SCHEMA_VERSION = "2" as const;

export interface RunProviderMetadata {
  providerId: string;
  providerKind: ProviderKind;
  adapterId: string;
  adapterVersion: string;
  model: string | null;
  promptVersion: PromptVersion;
}

export interface RunExecutionContextSummary {
  contextPackId: ContextPackDigest;
  inventoryId: EntityId;
  fileCount: number;
  textFileCount: number;
  binaryFileCount: number;
  totalFileBytes: number;
  totalPreviewBytes: number;
  truncatedTextFileCount: number;
  languages: readonly string[];
}

export interface RunExecutionResult {
  schemaVersion: typeof RUN_EXECUTION_SCHEMA_VERSION;
  taskSummary: string;
  interpretedIntent: string;
  context: RunExecutionContextSummary;
  warnings: readonly string[];
  recommendedNextSteps: readonly string[];
  proposalDraft: ChangeProposalDraft;
}

export type RunExecutionFailureCode =
  | "provider_execution_failed"
  | "structured_result_invalid";

export interface RunExecutionFailure {
  code: RunExecutionFailureCode;
  summary: string;
}

export interface RunExecution {
  provider: RunProviderMetadata;
  durationMs: number | null;
  result: RunExecutionResult | null;
  failure: RunExecutionFailure | null;
}
