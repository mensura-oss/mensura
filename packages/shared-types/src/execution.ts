import type { ContextPackDigest } from "./context-pack.js";
import type { EntityId } from "./domain.js";

export const RUN_EXECUTION_SCHEMA_VERSION = "1" as const;

export interface RunProviderMetadata {
  providerId: string;
  adapterId: string;
  adapterVersion: string;
  model: string | null;
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
