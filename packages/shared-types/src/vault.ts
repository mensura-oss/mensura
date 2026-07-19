import type { EntityId } from "./domain.js";

export const VAULT_INVENTORY_STATUSES = ["ready"] as const;
export const VAULT_FILE_KINDS = ["text", "binary"] as const;

export type VaultInventoryStatus = (typeof VAULT_INVENTORY_STATUSES)[number];
export type VaultFileKind = (typeof VAULT_FILE_KINDS)[number];

export interface VaultNamedCount {
  value: string;
  count: number;
}

export interface VaultInventorySummary {
  includedFileCount: number;
  excludedEntryCount: number;
  textFileCount: number;
  binaryFileCount: number;
  totalSizeBytes: number;
  extensions: readonly VaultNamedCount[];
  languages: readonly VaultNamedCount[];
}

export interface VaultInventorySnapshot {
  id: EntityId;
  workspaceId: EntityId;
  status: VaultInventoryStatus;
  builtAt: string;
  summary: VaultInventorySummary;
}

export interface VaultFileInventoryItem {
  path: string;
  name: string;
  extension: string | null;
  language: string | null;
  kind: VaultFileKind;
  sizeBytes: number;
}

export interface VaultFileCollection {
  inventoryId: EntityId;
  workspaceId: EntityId;
  items: readonly VaultFileInventoryItem[];
  total: number;
  returned: number;
}

export interface VaultFilePreview {
  inventoryId: EntityId;
  workspaceId: EntityId;
  file: VaultFileInventoryItem;
  encoding: "utf-8";
  text: string;
  previewBytes: number;
  totalBytes: number;
  truncated: boolean;
}
