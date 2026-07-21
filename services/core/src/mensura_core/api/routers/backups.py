from uuid import UUID

from fastapi import APIRouter, Response, status

from mensura_core.api.dependencies import BackupServiceDependency
from mensura_core.api.problems import (
    BACKUP_CONFLICT_RESPONSE,
    BACKUP_INTEGRITY_RESPONSE,
    BACKUP_RESTORE_RESPONSE,
    BACKUP_WRITE_RESPONSE,
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.backup_models import BackupArtifact, BackupCollection
from mensura_core.models import ResourceModel

router = APIRouter(tags=["backups"])


class CreateBackupBody(ResourceModel):
    label: str | None = None


@router.post(
    "/backups",
    response_model=BackupArtifact,
    status_code=status.HTTP_201_CREATED,
    responses={
        **BACKUP_WRITE_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Create a database backup",
)
def create_backup(
    payload: CreateBackupBody,
    response: Response,
    service: BackupServiceDependency,
) -> BackupArtifact:
    artifact = service.create_backup(label=payload.label)
    response.headers["Location"] = f"/api/v1/backups/{artifact.id}"
    return artifact


@router.get(
    "/backups",
    response_model=BackupCollection,
    responses={**VALIDATION_RESPONSE},
    summary="List all database backups",
)
async def list_backups(
    service: BackupServiceDependency,
) -> BackupCollection:
    return service.list_backups()


@router.get(
    "/backups/{backup_id}",
    response_model=BackupArtifact,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a database backup",
)
async def get_backup(
    backup_id: UUID,
    service: BackupServiceDependency,
) -> BackupArtifact:
    return service.get_backup(backup_id)


@router.post(
    "/backups/{backup_id}/restore",
    responses={
        **NOT_FOUND_RESPONSE,
        **BACKUP_CONFLICT_RESPONSE,
        **BACKUP_INTEGRITY_RESPONSE,
        **BACKUP_RESTORE_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Restore database from a backup",
)
def restore_backup(
    backup_id: UUID,
    service: BackupServiceDependency,
) -> dict[str, str]:
    message = service.restore_backup(backup_id)
    return {"message": message}
