import asyncio
import contextlib
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI

from mensura_core import __version__
from mensura_core.api.problems import install_problem_handlers
from mensura_core.api.router import router as v1_router
from mensura_core.api.routers.health import router as health_router
from mensura_core.application_repositories import (
    ApplicationRepository,
    InMemoryApplicationRepository,
)
from mensura_core.application_service import ChangeApplicationService
from mensura_core.backup_repositories import (
    BackupRepository,
    InMemoryBackupRepository,
)
from mensura_core.backup_service import BackupService
from mensura_core.change_proposal_repositories import (
    ChangeProposalRepository,
    InMemoryChangeProposalRepository,
)
from mensura_core.change_proposal_service import ChangeProposalService
from mensura_core.context_pack_repositories import (
    ContextPackRepository,
    InMemoryContextPackRepository,
)
from mensura_core.context_pack_service import ContextPackService
from mensura_core.event_publisher import InMemoryEventPublisher
from mensura_core.git_adapter import GitPythonRepositoryAdapter, GitRepositoryAdapter
from mensura_core.guard_config import GuardConfigurationLoader, JsonGuardConfigurationLoader
from mensura_core.guard_repositories import GuardRunRepository, InMemoryGuardRunRepository
from mensura_core.guard_runner import GuardCommandRunner, SubprocessGuardCommandRunner
from mensura_core.guard_service import GuardService
from mensura_core.job_repositories import InMemoryJobRepository, JobRepository
from mensura_core.job_service import JobService
from mensura_core.job_worker import JobWorker
from mensura_core.persistence import (
    SqlApplicationRepository,
    SqlBackupRepository,
    SqlChangeProposalRepository,
    SqlContextPackRepository,
    SqlCoreRepository,
    SqlGuardRunRepository,
    SqlJobRepository,
    SqlProposalVerificationRepository,
    SqlUndoRepository,
    SqlVaultInventoryRepository,
)
from mensura_core.persistence.database import (
    DEFAULT_BACKUP_DIR,
    create_persistence_engine,
    create_session_factory,
    extract_db_path,
    run_migrations,
)
from mensura_core.provider_adapter import (
    DeterministicReviewProvider,
    ProviderAdapter,
)
from mensura_core.provider_config import (
    CredentialStore,
    JsonProviderSettingsRepository,
    KeyringCredentialStore,
    ProviderSettingsRepository,
)
from mensura_core.provider_registry import ProviderRegistry, TransportFactory
from mensura_core.repositories import CoreRepository, InMemoryCoreRepository
from mensura_core.service import CoreService
from mensura_core.undo_repositories import (
    InMemoryUndoRepository,
    UndoRepository,
)
from mensura_core.undo_service import UndoService
from mensura_core.vault_inventory import LocalVaultInventoryBuilder, VaultInventoryBuilder
from mensura_core.vault_repositories import (
    InMemoryVaultInventoryRepository,
    VaultInventoryRepository,
)
from mensura_core.vault_service import VaultService
from mensura_core.verification_repositories import (
    InMemoryProposalVerificationRepository,
    ProposalVerificationRepository,
)
from mensura_core.verification_sandbox import (
    GitWorktreeSandboxFactory,
    VerificationSandboxFactory,
)
from mensura_core.verification_service import ProposalVerificationService

logger = logging.getLogger(__name__)


def create_app(
    repository: CoreRepository | None = None,
    git_repository: GitRepositoryAdapter | None = None,
    guard_configuration_loader: GuardConfigurationLoader | None = None,
    guard_command_runner: GuardCommandRunner | None = None,
    guard_run_repository: GuardRunRepository | None = None,
    vault_inventory_builder: VaultInventoryBuilder | None = None,
    vault_inventory_repository: VaultInventoryRepository | None = None,
    context_pack_repository: ContextPackRepository | None = None,
    change_proposal_repository: ChangeProposalRepository | None = None,
    provider: ProviderAdapter | None = None,
    provider_registry: ProviderRegistry | None = None,
    provider_settings_repository: ProviderSettingsRepository | None = None,
    credential_store: CredentialStore | None = None,
    openai_transport_factory: TransportFactory | None = None,
    verification_repository: ProposalVerificationRepository | None = None,
    verification_sandbox_factory: VerificationSandboxFactory | None = None,
    application_repository: ApplicationRepository | None = None,
    undo_repository: UndoRepository | None = None,
    backup_repository: BackupRepository | None = None,
    job_repository: JobRepository | None = None,
    *,
    run_migrations_on_startup: bool = False,
    database_url: str | None = None,
    use_sql: bool = False,
    enable_worker: bool = False,
) -> FastAPI:
    if run_migrations_on_startup:
        run_migrations(database_url)

    sf = None
    engine = None
    if use_sql:
        engine = create_persistence_engine(database_url)
        sf = create_session_factory(engine)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        worker_task: asyncio.Task[None] | None = None
        if enable_worker:
            worker: JobWorker = app.state.job_worker
            worker.recover_stale_jobs()
            worker_task = asyncio.create_task(worker.run_forever())
        try:
            yield
        finally:
            if worker_task is not None:
                worker_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await worker_task

    app = FastAPI(
        title="Mensura Core API",
        summary="Versioned task and run boundary for Mensura",
        version=__version__,
        docs_url="/docs",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    core_repository = (
        repository
        if repository is not None
        else (SqlCoreRepository(sf) if use_sql else InMemoryCoreRepository())
    )
    immutable_context_pack_repository = (
        context_pack_repository
        if context_pack_repository is not None
        else (SqlContextPackRepository(sf) if use_sql else InMemoryContextPackRepository())
    )
    providers = provider_registry or ProviderRegistry(
        provider_settings_repository or JsonProviderSettingsRepository(),
        credential_store or KeyringCredentialStore(),
        deterministic=provider or DeterministicReviewProvider(),
        **(
            {"openai_transport_factory": openai_transport_factory}
            if openai_transport_factory is not None
            else {}
        ),
    )
    app.state.provider_registry = providers
    event_publisher = InMemoryEventPublisher()
    app.state.event_publisher = event_publisher
    app.state.core_service = CoreService(
        core_repository,
        git_repository or GitPythonRepositoryAdapter(),
        immutable_context_pack_repository,
        providers,
        event_publisher=event_publisher,
    )
    configuration_loader = guard_configuration_loader or JsonGuardConfigurationLoader()
    command_runner = guard_command_runner or SubprocessGuardCommandRunner()
    app.state.guard_service = GuardService(
        core_repository,
        configuration_loader,
        command_runner,
        guard_run_repository
        if guard_run_repository is not None
        else (SqlGuardRunRepository(sf) if use_sql else InMemoryGuardRunRepository()),
    )
    inventory_repository = (
        vault_inventory_repository
        if vault_inventory_repository is not None
        else (SqlVaultInventoryRepository(sf) if use_sql else InMemoryVaultInventoryRepository())
    )
    app.state.vault_service = VaultService(
        core_repository,
        vault_inventory_builder or LocalVaultInventoryBuilder(),
        inventory_repository,
    )
    app.state.context_pack_service = ContextPackService(
        core_repository,
        inventory_repository,
        immutable_context_pack_repository,
    )
    proposal_repository = (
        change_proposal_repository
        if change_proposal_repository is not None
        else (SqlChangeProposalRepository(sf) if use_sql else InMemoryChangeProposalRepository())
    )
    app.state.change_proposal_service = ChangeProposalService(
        core_repository,
        immutable_context_pack_repository,
        proposal_repository,
    )
    verifications_repository = (
        verification_repository
        if verification_repository is not None
        else (
            SqlProposalVerificationRepository(sf)
            if use_sql
            else InMemoryProposalVerificationRepository()
        )
    )
    app.state.proposal_verification_service = ProposalVerificationService(
        core_repository,
        proposal_repository,
        verifications_repository,
        verification_sandbox_factory or GitWorktreeSandboxFactory(),
        configuration_loader,
        command_runner,
        event_publisher=event_publisher,
    )
    app_repo = (
        application_repository
        if application_repository is not None
        else (SqlApplicationRepository(sf) if use_sql else InMemoryApplicationRepository())
    )
    app.state.change_application_service = ChangeApplicationService(
        core_repository,
        proposal_repository,
        verifications_repository,
        app_repo,
        configuration_loader,
        command_runner,
        event_publisher=event_publisher,
    )
    undo_repo = (
        undo_repository
        if undo_repository is not None
        else (SqlUndoRepository(sf) if use_sql else InMemoryUndoRepository())
    )
    app.state.undo_service = UndoService(
        core_repository,
        app_repo,
        undo_repo,
        configuration_loader,
        command_runner,
        event_publisher=event_publisher,
    )
    backup_repo = (
        backup_repository
        if backup_repository is not None
        else (SqlBackupRepository(sf) if use_sql else InMemoryBackupRepository())
    )
    app.state.backup_service = BackupService(
        backup_repository=backup_repo,
        backup_dir=Path(os.environ.get("MENSURA_BACKUP_DIR", DEFAULT_BACKUP_DIR)),
        engine=engine if use_sql else None,
        db_path=Path(extract_db_path(database_url)) if database_url else None,
        event_publisher=event_publisher,
    )
    job_repo = (
        job_repository
        if job_repository is not None
        else (SqlJobRepository(sf) if use_sql else InMemoryJobRepository())
    )
    app.state.job_service = JobService(
        job_repo,
        proposal_repository,
        app_repo,
        event_publisher=event_publisher,
    )
    app.state.job_worker = JobWorker(
        job_repo,
        app.state.proposal_verification_service,
        app.state.change_application_service,
        app.state.undo_service,
        app.state.backup_service,
        event_publisher=event_publisher,
    )
    install_problem_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router)
    return app


app = create_app(
    repository=InMemoryCoreRepository(),
    guard_run_repository=InMemoryGuardRunRepository(),
    vault_inventory_repository=InMemoryVaultInventoryRepository(),
    context_pack_repository=InMemoryContextPackRepository(),
    change_proposal_repository=InMemoryChangeProposalRepository(),
    verification_repository=InMemoryProposalVerificationRepository(),
    application_repository=InMemoryApplicationRepository(),
    undo_repository=InMemoryUndoRepository(),
    run_migrations_on_startup=False,
)


def run() -> None:
    import uvicorn

    uvicorn.run(
        "mensura_core.main:create_sql_app",
        host="127.0.0.1",
        port=8000,
        factory=True,
    )


def create_sql_app() -> FastAPI:
    """App factory for production use: SQL-backed persistence, migrations, and the job worker."""
    return create_app(run_migrations_on_startup=True, use_sql=True, enable_worker=True)
