import type { EntityId, IsoDateTime } from "./domain.js";
import type { VaultNamedCount } from "./vault.js";

/**
 * Contracts for the Vault indexing / semantic-lexical retrieval / architecture
 * summary MVP (Core `/vault/index`, `/vault/search`, `/vault/memory/:id`,
 * `/vault/summarize`). These are distinct from the read-only inventory contracts
 * in `vault.ts`; the indexing layer is additive. Chunk embeddings are an internal
 * index artifact and are deliberately never exposed here.
 */

export const VAULT_SOURCE_TYPES = ["code", "doc", "config"] as const;
export type VaultSourceType = (typeof VAULT_SOURCE_TYPES)[number];

export const VAULT_INDEX_STATUSES = ["ready"] as const;
export type VaultIndexStatus = (typeof VAULT_INDEX_STATUSES)[number];

export const VAULT_SKIP_REASONS = [
  "excluded",
  "binary",
  "too_large",
  "unsupported_type",
  "empty",
  "read_error",
] as const;
export type VaultSkipReason = (typeof VAULT_SKIP_REASONS)[number];

/**
 * The lexical fallback strategy string. Core reports `strategy` dynamically:
 * `lexical-vector-cosine` when the offline lexical embedder is active,
 * `semantic-cosine:<backend>/<model>` when a real local embedding backend produced the
 * vectors, or `lexical-fallback:reindex-required` when the index was built by a different
 * backend than the one now configured (re-index to refresh).
 */
export const VAULT_SEARCH_STRATEGY = "lexical-vector-cosine";

export interface VaultSkippedFile {
  path: string;
  reason: VaultSkipReason;
}

/** Which embedding backend produced an index's chunk vectors. */
export interface VaultEmbeddingInfo {
  backend: string;
  model: string;
  dim: number;
  semantic: boolean;
}

export interface VaultIndexSummary {
  memoryItemCount: number;
  chunkCount: number;
  codeFileCount: number;
  docFileCount: number;
  configFileCount: number;
  totalSizeBytes: number;
  skippedCount: number;
  skippedByReason: readonly VaultNamedCount[];
  languages: readonly VaultNamedCount[];
  skippedSample: readonly VaultSkippedFile[];
  /** Absent on indexes built before this field existed (they were the lexical embedder). */
  embedding?: VaultEmbeddingInfo;
}

export interface VaultIndexSnapshot {
  id: EntityId;
  workspaceId: EntityId;
  status: VaultIndexStatus;
  indexedAt: IsoDateTime;
  summary: VaultIndexSummary;
}

export interface VaultChunk {
  id: EntityId;
  memoryItemId: EntityId;
  chunkIndex: number;
  startLine: number;
  endLine: number;
  charCount: number;
  digest: string;
  text: string;
}

export interface VaultMemoryItem {
  id: EntityId;
  workspaceId: EntityId;
  indexId: EntityId;
  path: string;
  sourceType: VaultSourceType;
  language: string | null;
  digest: string;
  sizeBytes: number;
  chunkCount: number;
  indexedAt: IsoDateTime;
}

export interface VaultMemoryItemDetail {
  item: VaultMemoryItem;
  chunks: readonly VaultChunk[];
}

export interface VaultSearchHit {
  memoryItemId: EntityId;
  chunkId: EntityId;
  path: string;
  sourceType: VaultSourceType;
  language: string | null;
  chunkIndex: number;
  startLine: number;
  endLine: number;
  score: number;
  snippet: string;
}

export interface VaultSearchResponse {
  workspaceId: EntityId;
  indexId: EntityId;
  query: string;
  strategy: string;
  total: number;
  returned: number;
  hits: readonly VaultSearchHit[];
}

export interface VaultSearchOptions {
  query: string;
  limit?: number;
  sourceType?: VaultSourceType;
}

export interface VaultModuleSummary {
  name: string;
  path: string;
  fileCount: number;
  totalSizeBytes: number;
  primaryLanguage: string | null;
}

export interface VaultArchitectureSummary {
  workspaceId: EntityId;
  indexId: EntityId;
  generatedAt: IsoDateTime;
  fileCount: number;
  codeFileCount: number;
  docFileCount: number;
  configFileCount: number;
  totalSizeBytes: number;
  languages: readonly VaultNamedCount[];
  modules: readonly VaultModuleSummary[];
  technologies: readonly string[];
  entryPoints: readonly string[];
}
