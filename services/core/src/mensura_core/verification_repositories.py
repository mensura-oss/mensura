from collections.abc import Sequence
from threading import RLock
from typing import Protocol
from uuid import UUID

from mensura_core.verification_models import ProposalVerification


class ProposalVerificationRepository(Protocol):
    def save(self, verification: ProposalVerification) -> None: ...

    def get(self, verification_id: UUID) -> ProposalVerification | None: ...

    def list_for_proposal(self, proposal_id: UUID) -> Sequence[ProposalVerification]: ...


class InMemoryProposalVerificationRepository:
    """Process-local storage for immutable verification artifacts."""

    def __init__(self) -> None:
        self._verifications: dict[UUID, ProposalVerification] = {}
        self._lock = RLock()

    def save(self, verification: ProposalVerification) -> None:
        with self._lock:
            self._verifications[verification.id] = verification

    def get(self, verification_id: UUID) -> ProposalVerification | None:
        with self._lock:
            return self._verifications.get(verification_id)

    def list_for_proposal(self, proposal_id: UUID) -> Sequence[ProposalVerification]:
        with self._lock:
            return tuple(
                sorted(
                    (
                        verification
                        for verification in self._verifications.values()
                        if verification.proposal_id == proposal_id
                    ),
                    key=lambda verification: (verification.created_at, verification.id),
                )
            )
