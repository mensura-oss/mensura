import codecs
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import UUID, uuid4

from mensura_core.exceptions import (
    ResourceNotFoundError,
    VaultBinaryPreviewError,
    VaultFileExcludedError,
    VaultFileNotFoundError,
    VaultInventoryNotBuiltError,
    VaultPathInvalidError,
    VaultRootInvalidError,
)
from mensura_core.models import Workspace, ensure_utc_timestamp
from mensura_core.repositories import CoreRepository
from mensura_core.vault_inventory import (
    MAX_INCLUDED_FILE_BYTES,
    VaultInventoryBuilder,
    VaultInventoryRules,
    count_values,
)
from mensura_core.vault_models import (
    VaultFileCollection,
    VaultFileKind,
    VaultFilePreview,
    VaultInventorySnapshot,
    VaultInventorySummary,
    VaultNamedCount,
)
from mensura_core.vault_repositories import VaultInventoryRecord, VaultInventoryRepository

PREVIEW_LIMIT_BYTES = 16 * 1024
IdFactory = Callable[[], UUID]
Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


class VaultService:
    """Manual deterministic inventory and bounded file retrieval service."""

    def __init__(
        self,
        core_repository: CoreRepository,
        inventory_builder: VaultInventoryBuilder,
        inventory_repository: VaultInventoryRepository,
        *,
        rules: VaultInventoryRules | None = None,
        id_factory: IdFactory = uuid4,
        clock: Clock = utc_now,
    ) -> None:
        self._core_repository = core_repository
        self._inventory_builder = inventory_builder
        self._inventory_repository = inventory_repository
        self._rules = rules or VaultInventoryRules()
        self._id_factory = id_factory
        self._clock = clock

    def build_inventory(self, workspace_id: UUID) -> VaultInventorySnapshot:
        workspace = self._require_workspace(workspace_id)
        built = self._inventory_builder.build(workspace.root_path)
        items = built.items
        extension_counts = count_values([item.extension for item in items])
        language_counts = count_values([item.language for item in items])
        snapshot = VaultInventorySnapshot(
            id=self._id_factory(),
            workspace_id=workspace.id,
            built_at=ensure_utc_timestamp(self._clock()),
            summary=VaultInventorySummary(
                included_file_count=len(items),
                excluded_entry_count=built.excluded_entry_count,
                text_file_count=sum(item.kind is VaultFileKind.TEXT for item in items),
                binary_file_count=sum(item.kind is VaultFileKind.BINARY for item in items),
                total_size_bytes=sum(item.size_bytes for item in items),
                extensions=self._named_counts(extension_counts),
                languages=self._named_counts(language_counts),
            ),
        )
        self._inventory_repository.save_latest(VaultInventoryRecord(snapshot, items))
        return snapshot

    def get_inventory(self, workspace_id: UUID) -> VaultInventorySnapshot:
        self._require_workspace(workspace_id)
        return self._require_inventory(workspace_id).snapshot

    def list_files(
        self,
        workspace_id: UUID,
        *,
        query: str | None,
        extension: str | None,
        limit: int,
    ) -> VaultFileCollection:
        self._require_workspace(workspace_id)
        record = self._require_inventory(workspace_id)
        normalized_query = query.casefold().strip() if query else None
        normalized_extension = self._normalize_extension(extension)
        matching = [
            item
            for item in record.items
            if (not normalized_query or normalized_query in item.path.casefold())
            and (not normalized_extension or item.extension == normalized_extension)
        ]
        returned = matching[:limit]
        return VaultFileCollection(
            inventory_id=record.snapshot.id,
            workspace_id=workspace_id,
            items=returned,
            total=len(matching),
            returned=len(returned),
        )

    def get_file_preview(self, workspace_id: UUID, relative_path: str) -> VaultFilePreview:
        workspace = self._require_workspace(workspace_id)
        record = self._require_inventory(workspace_id)
        normalized_path = self._normalize_path(relative_path)
        item = next((item for item in record.items if item.path == normalized_path), None)
        root, target = self._resolve_preview_target(workspace, normalized_path)

        if item is None:
            try:
                size_bytes = target.stat().st_size if target.is_file() else None
            except OSError:
                size_bytes = None
            if self._rules.excludes_relative_path(normalized_path, size_bytes=size_bytes):
                raise VaultFileExcludedError(normalized_path)
            raise VaultFileNotFoundError(normalized_path)
        if item.kind is VaultFileKind.BINARY:
            raise VaultBinaryPreviewError(normalized_path)

        if target.is_symlink() or not target.is_file() or not target.is_relative_to(root):
            raise VaultFileExcludedError(normalized_path)
        try:
            total_bytes = target.stat().st_size
        except OSError as error:
            raise VaultFileNotFoundError(normalized_path) from error
        if total_bytes > MAX_INCLUDED_FILE_BYTES:
            raise VaultFileExcludedError(normalized_path)

        try:
            with target.open("rb") as stream:
                data = stream.read(PREVIEW_LIMIT_BYTES + 1)
        except OSError as error:
            raise VaultFileNotFoundError(normalized_path) from error
        if b"\0" in data:
            raise VaultBinaryPreviewError(normalized_path)

        truncated = total_bytes > PREVIEW_LIMIT_BYTES or len(data) > PREVIEW_LIMIT_BYTES
        preview_data = data[:PREVIEW_LIMIT_BYTES]
        try:
            decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
            text = decoder.decode(preview_data, final=not truncated)
            buffered, _state = decoder.getstate()
        except UnicodeDecodeError as error:
            raise VaultBinaryPreviewError(normalized_path) from error
        preview_bytes = len(preview_data) - len(buffered)
        return VaultFilePreview(
            inventory_id=record.snapshot.id,
            workspace_id=workspace_id,
            file=item,
            text=text,
            preview_bytes=preview_bytes,
            total_bytes=total_bytes,
            truncated=truncated,
        )

    def _require_workspace(self, workspace_id: UUID) -> Workspace:
        workspace = self._core_repository.get_workspace(workspace_id)
        if workspace is None:
            raise ResourceNotFoundError("Workspace", workspace_id)
        return workspace

    def _require_inventory(self, workspace_id: UUID) -> VaultInventoryRecord:
        record = self._inventory_repository.get_latest(workspace_id)
        if record is None:
            raise VaultInventoryNotBuiltError(workspace_id)
        return record

    def _resolve_preview_target(
        self, workspace: Workspace, relative_path: str
    ) -> tuple[Path, Path]:
        root = Path(workspace.root_path)
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as error:
            raise VaultRootInvalidError(workspace.root_path) from error
        if not resolved_root.is_dir():
            raise VaultRootInvalidError(workspace.root_path)

        unresolved_target = resolved_root
        for part in PurePosixPath(relative_path).parts:
            unresolved_target /= part
            if unresolved_target.is_symlink():
                raise VaultFileExcludedError(relative_path)
        try:
            target = unresolved_target.resolve(strict=True)
        except OSError as error:
            raise VaultFileNotFoundError(relative_path) from error
        if not target.is_relative_to(resolved_root):
            raise VaultFileExcludedError(relative_path)
        return resolved_root, target

    def _normalize_path(self, relative_path: str) -> str:
        if not relative_path or "\0" in relative_path or "\\" in relative_path:
            raise VaultPathInvalidError()
        path = PurePosixPath(relative_path)
        if path.is_absolute() or str(path) != relative_path or ".." in path.parts:
            raise VaultPathInvalidError()
        return path.as_posix()

    def _normalize_extension(self, extension: str | None) -> str | None:
        if not extension or not extension.strip():
            return None
        normalized = extension.strip().casefold()
        return normalized if normalized.startswith(".") else f".{normalized}"

    def _named_counts(self, counts: dict[str, int]) -> list[VaultNamedCount]:
        return [VaultNamedCount(value=value, count=counts[value]) for value in sorted(counts)]
