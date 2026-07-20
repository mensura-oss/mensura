from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.application_models import ApplicationArtifact


class ApplicationRepository(Protocol):
    def save_if_absent_for_proposal(self, application: ApplicationArtifact) -> bool: ...

    def get(self, application_id: UUID) -> ApplicationArtifact | None: ...

    def get_for_proposal(self, proposal_id: UUID) -> ApplicationArtifact | None: ...

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ApplicationArtifact]: ...


class InMemoryApplicationRepository:
    """Process-local storage with single-apply semantics per change proposal."""

    def __init__(self) -> None:
        self._applications: dict[UUID, ApplicationArtifact] = {}
        self._application_ids_by_proposal: dict[UUID, UUID] = {}
        self._lock = RLock()

    def save_if_absent_for_proposal(self, application: ApplicationArtifact) -> bool:
        with self._lock:
            if application.proposal_id in self._application_ids_by_proposal:
                return False
            self._applications[application.id] = application
            self._application_ids_by_proposal[application.proposal_id] = application.id
            return True

    def get(self, application_id: UUID) -> ApplicationArtifact | None:
        with self._lock:
            return self._applications.get(application_id)

    def get_for_proposal(self, proposal_id: UUID) -> ApplicationArtifact | None:
        with self._lock:
            application_id = self._application_ids_by_proposal.get(proposal_id)
            return self._applications.get(application_id) if application_id is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ApplicationArtifact]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        application
                        for application in self._applications.values()
                        if application.workspace_id == workspace_id
                    ),
                    key=lambda application: (application.created_at, application.id),
                )
            )
