from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.persistence.models import ProposalVerificationRow
from mensura_core.verification_models import ProposalVerification


class SqlProposalVerificationRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def save(self, verification: ProposalVerification) -> None:
        with self._sf() as session:
            session.add(ProposalVerificationRow.from_domain(verification))
            session.commit()

    def get(self, verification_id: UUID) -> ProposalVerification | None:
        with self._sf() as session:
            row = session.get(ProposalVerificationRow, verification_id)
            return row.to_domain() if row is not None else None

    def list_for_proposal(self, proposal_id: UUID) -> Sequence[ProposalVerification]:
        with self._sf() as session:
            rows = (
                session.query(ProposalVerificationRow)
                .filter(ProposalVerificationRow.proposal_id == proposal_id)
                .order_by(ProposalVerificationRow.created_at, ProposalVerificationRow.id)
                .all()
            )
            return tuple(row.to_domain() for row in rows)
