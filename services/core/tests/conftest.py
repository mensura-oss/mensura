import pytest
from fastapi.testclient import TestClient

from mensura_core.application_repositories import InMemoryApplicationRepository
from mensura_core.backup_repositories import InMemoryBackupRepository
from mensura_core.change_proposal_repositories import InMemoryChangeProposalRepository
from mensura_core.context_pack_repositories import InMemoryContextPackRepository
from mensura_core.guard_repositories import InMemoryGuardRunRepository
from mensura_core.job_repositories import InMemoryJobRepository
from mensura_core.main import create_app
from mensura_core.repositories import InMemoryCoreRepository
from mensura_core.undo_repositories import InMemoryUndoRepository
from mensura_core.vault_repositories import InMemoryVaultInventoryRepository
from mensura_core.verification_repositories import InMemoryProposalVerificationRepository


@pytest.fixture
def client() -> TestClient:
    with TestClient(
        create_app(
            repository=InMemoryCoreRepository(),
            guard_run_repository=InMemoryGuardRunRepository(),
            vault_inventory_repository=InMemoryVaultInventoryRepository(),
            context_pack_repository=InMemoryContextPackRepository(),
            change_proposal_repository=InMemoryChangeProposalRepository(),
            verification_repository=InMemoryProposalVerificationRepository(),
            application_repository=InMemoryApplicationRepository(),
            undo_repository=InMemoryUndoRepository(),
            backup_repository=InMemoryBackupRepository(),
            job_repository=InMemoryJobRepository(),
            run_migrations_on_startup=False,
        )
    ) as test_client:
        yield test_client
