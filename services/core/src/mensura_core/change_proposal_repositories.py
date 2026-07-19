from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.change_proposal_models import (
    ChangeProposal,
    ChangeProposalStatus,
)


class ChangeProposalRepository(Protocol):
    def save_if_absent_for_run(self, proposal: ChangeProposal) -> bool: ...

    def get(self, proposal_id: UUID) -> ChangeProposal | None: ...

    def get_for_run(self, run_id: UUID) -> ChangeProposal | None: ...

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ChangeProposal]: ...

    def replace_if_status(
        self,
        proposal: ChangeProposal,
        expected_status: ChangeProposalStatus,
    ) -> bool: ...


class InMemoryChangeProposalRepository:
    """Process-local proposal storage with one idempotent artifact per source run."""

    def __init__(self) -> None:
        self._proposals: dict[UUID, ChangeProposal] = {}
        self._proposal_ids_by_run: dict[UUID, UUID] = {}
        self._lock = RLock()

    def save_if_absent_for_run(self, proposal: ChangeProposal) -> bool:
        with self._lock:
            if proposal.run_id in self._proposal_ids_by_run:
                return False
            self._proposals[proposal.id] = proposal
            self._proposal_ids_by_run[proposal.run_id] = proposal.id
            return True

    def get(self, proposal_id: UUID) -> ChangeProposal | None:
        with self._lock:
            return self._proposals.get(proposal_id)

    def get_for_run(self, run_id: UUID) -> ChangeProposal | None:
        with self._lock:
            proposal_id = self._proposal_ids_by_run.get(run_id)
            return self._proposals.get(proposal_id) if proposal_id is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ChangeProposal]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        proposal
                        for proposal in self._proposals.values()
                        if proposal.workspace_id == workspace_id
                    ),
                    key=lambda proposal: (proposal.created_at, proposal.id),
                )
            )

    def replace_if_status(
        self,
        proposal: ChangeProposal,
        expected_status: ChangeProposalStatus,
    ) -> bool:
        with self._lock:
            current = self._proposals.get(proposal.id)
            if current is None or current.status is not expected_status:
                return False
            self._proposals[proposal.id] = proposal
            return True
