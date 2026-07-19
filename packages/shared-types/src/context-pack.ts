import type { EntityId } from "./domain.js";
import type { VaultFileKind } from "./vault.js";

export const CONTEXT_PACK_SCHEMA_VERSION = "1" as const;
export const CONTEXT_PACK_CAPTURE_MODES = ["text_preview", "metadata_only"] as const;

export type ContextPackCaptureMode = (typeof CONTEXT_PACK_CAPTURE_MODES)[number];
export type ContextPackDigest = `sha256:${string}`;

export interface ContextPackLimits {
  maxFiles: number;
  maxPreviewBytesPerFile: number;
  maxTotalPreviewBytes: number;
}

export interface ContextPackFileEntry {
  path: string;
  name: string;
  extension: string | null;
  language: string | null;
  kind: VaultFileKind;
  sizeBytes: number;
  contentDigest: ContextPackDigest;
  captureMode: ContextPackCaptureMode;
  encoding: "utf-8" | null;
  previewText: string | null;
  previewBytes: number;
  totalBytes: number;
  truncated: boolean;
}

export interface ContextPackFileSummary {
  fileCount: number;
  textFileCount: number;
  binaryFileCount: number;
  totalFileBytes: number;
  totalPreviewBytes: number;
  truncatedTextFileCount: number;
}

export interface ContextPackSummary {
  id: ContextPackDigest;
  digest: ContextPackDigest;
  workspaceId: EntityId;
  inventoryId: EntityId;
  schemaVersion: typeof CONTEXT_PACK_SCHEMA_VERSION;
  summary: ContextPackFileSummary;
}

/** Compact immutable evidence reference embedded in run read models. */
export interface ContextPackReference {
  id: ContextPackDigest;
  workspaceId: EntityId;
  inventoryId: EntityId;
  schemaVersion: typeof CONTEXT_PACK_SCHEMA_VERSION;
  fileCount: number;
  totalFileBytes: number;
  totalPreviewBytes: number;
}

export interface ContextPackManifest extends ContextPackSummary {
  limits: ContextPackLimits;
  files: readonly ContextPackFileEntry[];
}

export interface CreateContextPackRequest {
  paths: readonly string[];
}

export interface CreateContextPackResponse {
  contextPack: ContextPackManifest;
  created: boolean;
}

export interface ContextPackCollection {
  items: readonly ContextPackSummary[];
  total: number;
}
