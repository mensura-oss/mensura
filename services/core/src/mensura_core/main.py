from fastapi import FastAPI

from mensura_core import __version__
from mensura_core.api.problems import install_problem_handlers
from mensura_core.api.router import router as v1_router
from mensura_core.api.routers.health import router as health_router
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
from mensura_core.git_adapter import GitPythonRepositoryAdapter, GitRepositoryAdapter
from mensura_core.guard_config import GuardConfigurationLoader, JsonGuardConfigurationLoader
from mensura_core.guard_repositories import GuardRunRepository, InMemoryGuardRunRepository
from mensura_core.guard_runner import GuardCommandRunner, SubprocessGuardCommandRunner
from mensura_core.guard_service import GuardService
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
from mensura_core.vault_inventory import LocalVaultInventoryBuilder, VaultInventoryBuilder
from mensura_core.vault_repositories import (
    InMemoryVaultInventoryRepository,
    VaultInventoryRepository,
)
from mensura_core.vault_service import VaultService


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
) -> FastAPI:
    app = FastAPI(
        title="Mensura Core API",
        summary="Versioned task and run boundary for Mensura",
        version=__version__,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    core_repository = repository or InMemoryCoreRepository()
    immutable_context_pack_repository = context_pack_repository or InMemoryContextPackRepository()
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
    app.state.core_service = CoreService(
        core_repository,
        git_repository or GitPythonRepositoryAdapter(),
        immutable_context_pack_repository,
        providers,
    )
    app.state.guard_service = GuardService(
        core_repository,
        guard_configuration_loader or JsonGuardConfigurationLoader(),
        guard_command_runner or SubprocessGuardCommandRunner(),
        guard_run_repository or InMemoryGuardRunRepository(),
    )
    inventory_repository = vault_inventory_repository or InMemoryVaultInventoryRepository()
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
    app.state.change_proposal_service = ChangeProposalService(
        core_repository,
        immutable_context_pack_repository,
        change_proposal_repository or InMemoryChangeProposalRepository(),
    )
    install_problem_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("mensura_core.main:app", host="127.0.0.1", port=8000)
