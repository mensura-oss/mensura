from typing import Annotated, cast

from fastapi import Depends, Request

from mensura_core.application_service import ChangeApplicationService
from mensura_core.backup_service import BackupService
from mensura_core.change_proposal_service import ChangeProposalService
from mensura_core.context_pack_service import ContextPackService
from mensura_core.guard_service import GuardService
from mensura_core.job_service import JobService
from mensura_core.provider_registry import ProviderRegistry
from mensura_core.service import CoreService
from mensura_core.undo_service import UndoService
from mensura_core.vault_service import VaultService
from mensura_core.verification_service import ProposalVerificationService


def get_core_service(request: Request) -> CoreService:
    return cast(CoreService, request.app.state.core_service)


CoreServiceDependency = Annotated[CoreService, Depends(get_core_service)]


def get_guard_service(request: Request) -> GuardService:
    return cast(GuardService, request.app.state.guard_service)


GuardServiceDependency = Annotated[GuardService, Depends(get_guard_service)]


def get_vault_service(request: Request) -> VaultService:
    return cast(VaultService, request.app.state.vault_service)


VaultServiceDependency = Annotated[VaultService, Depends(get_vault_service)]


def get_context_pack_service(request: Request) -> ContextPackService:
    return cast(ContextPackService, request.app.state.context_pack_service)


ContextPackServiceDependency = Annotated[ContextPackService, Depends(get_context_pack_service)]


def get_change_proposal_service(request: Request) -> ChangeProposalService:
    return cast(ChangeProposalService, request.app.state.change_proposal_service)


ChangeProposalServiceDependency = Annotated[
    ChangeProposalService,
    Depends(get_change_proposal_service),
]


def get_proposal_verification_service(request: Request) -> ProposalVerificationService:
    return cast(ProposalVerificationService, request.app.state.proposal_verification_service)


ProposalVerificationServiceDependency = Annotated[
    ProposalVerificationService,
    Depends(get_proposal_verification_service),
]


def get_change_application_service(request: Request) -> ChangeApplicationService:
    return cast(ChangeApplicationService, request.app.state.change_application_service)


ChangeApplicationServiceDependency = Annotated[
    ChangeApplicationService,
    Depends(get_change_application_service),
]


def get_undo_service(request: Request) -> UndoService:
    return cast(UndoService, request.app.state.undo_service)


UndoServiceDependency = Annotated[
    UndoService,
    Depends(get_undo_service),
]


def get_provider_registry(request: Request) -> ProviderRegistry:
    return cast(ProviderRegistry, request.app.state.provider_registry)


ProviderRegistryDependency = Annotated[ProviderRegistry, Depends(get_provider_registry)]


def get_backup_service(request: Request) -> BackupService:
    return cast(BackupService, request.app.state.backup_service)


BackupServiceDependency = Annotated[BackupService, Depends(get_backup_service)]


def get_job_service(request: Request) -> JobService:
    return cast(JobService, request.app.state.job_service)


JobServiceDependency = Annotated[JobService, Depends(get_job_service)]
