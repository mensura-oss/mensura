from __future__ import annotations

import codecs
import hashlib
import json
from pathlib import Path, PurePosixPath
from uuid import UUID

from mensura_core.context_pack_models import (
    CONTEXT_PACK_SCHEMA_VERSION,
    ContextPackCollection,
    ContextPackFileEntry,
    ContextPackFileSummary,
    ContextPackLimits,
    ContextPackManifest,
    ContextPackSummary,
    CreateContextPackRequest,
    CreateContextPackResponse,
)
from mensura_core.context_pack_repositories import ContextPackRepository
from mensura_core.exceptions import (
    ContextPackFileChangedError,
    ContextPackInvalidSelectionError,
    ContextPackNotFoundError,
    ContextPackTooLargeError,
    ResourceNotFoundError,
    VaultFileExcludedError,
    VaultInventoryNotBuiltError,
    VaultPathInvalidError,
    VaultRootInvalidError,
)
from mensura_core.models import Workspace
from mensura_core.repositories import CoreRepository
from mensura_core.vault_inventory import MAX_INCLUDED_FILE_BYTES, VaultInventoryRules
from mensura_core.vault_models import VaultFileInventoryItem, VaultFileKind
from mensura_core.vault_repositories import VaultInventoryRecord, VaultInventoryRepository

MAX_CONTEXT_PACK_FILES = 50
MAX_PREVIEW_BYTES_PER_FILE = 16 * 1024
MAX_TOTAL_PREVIEW_BYTES = 256 * 1024
HASH_CHUNK_BYTES = 64 * 1024


class ContextPackService:
    """Create exact, bounded, immutable manifests from one Vault inventory snapshot."""

    def __init__(
        self,
        core_repository: CoreRepository,
        inventory_repository: VaultInventoryRepository,
        context_pack_repository: ContextPackRepository,
        *,
        rules: VaultInventoryRules | None = None,
    ) -> None:
        self._core_repository = core_repository
        self._inventory_repository = inventory_repository
        self._context_pack_repository = context_pack_repository
        self._rules = rules or VaultInventoryRules()
        self._limits = ContextPackLimits(
            max_files=MAX_CONTEXT_PACK_FILES,
            max_preview_bytes_per_file=MAX_PREVIEW_BYTES_PER_FILE,
            max_total_preview_bytes=MAX_TOTAL_PREVIEW_BYTES,
        )

    def create(
        self,
        workspace_id: UUID,
        request: CreateContextPackRequest,
    ) -> CreateContextPackResponse:
        workspace = self._require_workspace(workspace_id)
        inventory = self._require_inventory(workspace_id)
        paths = self._normalize_paths(request.paths)
        if len(paths) > MAX_CONTEXT_PACK_FILES:
            raise ContextPackTooLargeError(
                f"A context pack may include at most {MAX_CONTEXT_PACK_FILES} files."
            )

        items_by_path = {item.path: item for item in inventory.items}
        selected_items: list[VaultFileInventoryItem] = []
        for path in paths:
            item = items_by_path.get(path)
            if item is None:
                if self._rules.excludes_relative_path(path):
                    raise VaultFileExcludedError(path)
                raise ContextPackInvalidSelectionError(
                    f"File '{path}' is not present in the latest Vault inventory."
                )
            selected_items.append(item)

        root = self._resolve_root(workspace)
        entries: list[ContextPackFileEntry] = []
        total_preview_bytes = 0
        for item in selected_items:
            entry = self._capture_entry(root, item)
            total_preview_bytes += entry.preview_bytes
            if total_preview_bytes > MAX_TOTAL_PREVIEW_BYTES:
                raise ContextPackTooLargeError(
                    "Selected text previews exceed the 256 KiB context-pack limit."
                )
            entries.append(entry)

        summary = ContextPackFileSummary(
            file_count=len(entries),
            text_file_count=sum(entry.kind is VaultFileKind.TEXT for entry in entries),
            binary_file_count=sum(entry.kind is VaultFileKind.BINARY for entry in entries),
            total_file_bytes=sum(entry.total_bytes for entry in entries),
            total_preview_bytes=total_preview_bytes,
            truncated_text_file_count=sum(
                entry.kind is VaultFileKind.TEXT and entry.truncated for entry in entries
            ),
        )
        digest = self._manifest_digest(
            workspace_id=workspace_id,
            inventory_id=inventory.snapshot.id,
            summary=summary,
            entries=entries,
        )
        manifest = ContextPackManifest(
            id=digest,
            digest=digest,
            workspace_id=workspace_id,
            inventory_id=inventory.snapshot.id,
            summary=summary,
            limits=self._limits,
            files=tuple(entries),
        )
        created = self._context_pack_repository.save_if_absent(manifest)
        stored = self._context_pack_repository.get(workspace_id, digest)
        return CreateContextPackResponse(
            context_pack=stored or manifest,
            created=created,
        )

    def list(self, workspace_id: UUID) -> ContextPackCollection:
        self._require_workspace(workspace_id)
        manifests = self._context_pack_repository.list_for_workspace(workspace_id)
        items = [self._to_summary(manifest) for manifest in manifests]
        return ContextPackCollection(items=items, total=len(items))

    def get(self, workspace_id: UUID, context_pack_id: str) -> ContextPackManifest:
        self._require_workspace(workspace_id)
        manifest = self._context_pack_repository.get(workspace_id, context_pack_id)
        if manifest is None:
            raise ContextPackNotFoundError(context_pack_id)
        return manifest

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._core_repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace

    def _require_inventory(self, workspace_id: UUID) -> VaultInventoryRecord:
        inventory = self._inventory_repository.get_latest(workspace_id)
        if inventory is None:
            raise VaultInventoryNotBuiltError(workspace_id)
        return inventory

    def _normalize_paths(self, raw_paths: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for raw_path in raw_paths:
            if not raw_path or "\0" in raw_path or "\\" in raw_path:
                raise VaultPathInvalidError()
            path = PurePosixPath(raw_path)
            if path.is_absolute() or str(path) != raw_path or ".." in path.parts:
                raise VaultPathInvalidError()
            canonical = path.as_posix()
            if canonical in seen:
                raise ContextPackInvalidSelectionError(
                    f"File '{canonical}' was selected more than once."
                )
            seen.add(canonical)
            normalized.append(canonical)
        return sorted(normalized, key=lambda value: (value.casefold(), value))

    def _resolve_root(self, workspace: Workspace) -> Path:
        try:
            root = Path(workspace.root_path).resolve(strict=True)
        except OSError as error:
            raise VaultRootInvalidError(workspace.root_path) from error
        if not root.is_dir():
            raise VaultRootInvalidError(workspace.root_path)
        return root

    def _resolve_target(self, root: Path, relative_path: str) -> Path:
        unresolved_target = root
        for part in PurePosixPath(relative_path).parts:
            unresolved_target /= part
            if unresolved_target.is_symlink():
                raise VaultFileExcludedError(relative_path)
        try:
            target = unresolved_target.resolve(strict=True)
        except OSError as error:
            raise ContextPackFileChangedError(relative_path) from error
        if not target.is_relative_to(root) or target.is_symlink() or not target.is_file():
            raise VaultFileExcludedError(relative_path)
        return target

    def _capture_entry(
        self,
        root: Path,
        item: VaultFileInventoryItem,
    ) -> ContextPackFileEntry:
        target = self._resolve_target(root, item.path)
        try:
            size_bytes = target.stat().st_size
        except OSError as error:
            raise ContextPackFileChangedError(item.path) from error
        if self._rules.excludes_relative_path(item.path, size_bytes=size_bytes):
            raise VaultFileExcludedError(item.path)
        if size_bytes != item.size_bytes or size_bytes > MAX_INCLUDED_FILE_BYTES:
            raise ContextPackFileChangedError(item.path)

        hasher = hashlib.sha256()
        preview_data = bytearray()
        bytes_read = 0
        try:
            with target.open("rb") as stream:
                while chunk := stream.read(HASH_CHUNK_BYTES):
                    bytes_read += len(chunk)
                    hasher.update(chunk)
                    if len(preview_data) < MAX_PREVIEW_BYTES_PER_FILE:
                        remaining = MAX_PREVIEW_BYTES_PER_FILE - len(preview_data)
                        preview_data.extend(chunk[:remaining])
        except OSError as error:
            raise ContextPackFileChangedError(item.path) from error
        if bytes_read != size_bytes:
            raise ContextPackFileChangedError(item.path)

        digest = f"sha256:{hasher.hexdigest()}"
        if item.kind is VaultFileKind.BINARY:
            return ContextPackFileEntry(
                **item.model_dump(),
                content_digest=digest,
                capture_mode="metadata_only",
                encoding=None,
                preview_text=None,
                preview_bytes=0,
                total_bytes=size_bytes,
                truncated=False,
            )

        if b"\0" in preview_data:
            raise ContextPackFileChangedError(item.path)
        truncated = size_bytes > MAX_PREVIEW_BYTES_PER_FILE
        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
            text = decoder.decode(bytes(preview_data), final=not truncated)
            buffered, _state = decoder.getstate()
        except UnicodeDecodeError as error:
            raise ContextPackFileChangedError(item.path) from error
        preview_bytes = len(preview_data) - len(buffered)
        return ContextPackFileEntry(
            **item.model_dump(),
            content_digest=digest,
            capture_mode="text_preview",
            encoding="utf-8",
            preview_text=text,
            preview_bytes=preview_bytes,
            total_bytes=size_bytes,
            truncated=truncated,
        )

    def _manifest_digest(
        self,
        *,
        workspace_id: UUID,
        inventory_id: UUID,
        summary: ContextPackFileSummary,
        entries: list[ContextPackFileEntry],
    ) -> str:
        payload = {
            "schemaVersion": CONTEXT_PACK_SCHEMA_VERSION,
            "workspaceId": str(workspace_id),
            "inventoryId": str(inventory_id),
            "limits": self._limits.model_dump(mode="json", by_alias=True),
            "summary": summary.model_dump(mode="json", by_alias=True),
            "files": [entry.model_dump(mode="json", by_alias=True) for entry in entries],
        }
        canonical_json = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return f"sha256:{hashlib.sha256(canonical_json).hexdigest()}"

    def _to_summary(self, manifest: ContextPackManifest) -> ContextPackSummary:
        return ContextPackSummary(
            id=manifest.id,
            digest=manifest.digest,
            workspace_id=manifest.workspace_id,
            inventory_id=manifest.inventory_id,
            schema_version=manifest.schema_version,
            summary=manifest.summary,
        )
