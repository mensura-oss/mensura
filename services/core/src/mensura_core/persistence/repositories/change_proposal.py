from collections.abc import Callable, Sequence
from uuid import UUID

from sqlalchemy.orm import Session

from mensura_core.change_proposal_models import ChangeProposal, ChangeProposalStatus
from mensura_core.persistence.models import ChangeProposalRow


class SqlChangeProposalRepository:
    def __init__(self, session_factory: Callable[[], Session]) -> None:
        self._sf = session_factory

    def save_if_absent_for_run(self, proposal: ChangeProposal) -> bool:
        with self._sf() as session:
            existing = (
                session.query(ChangeProposalRow)
                .filter(ChangeProposalRow.run_id == proposal.run_id)
                .first()
            )
            if existing is not None:
                return False
            session.add(ChangeProposalRow.from_domain(proposal))
            session.commit()
            return True

    def get(self, proposal_id: UUID) -> ChangeProposal | None:
        with self._sf() as session:
            row = session.get(ChangeProposalRow, proposal_id)
            return row.to_domain() if row is not None else None

    def get_for_run(self, run_id: UUID) -> ChangeProposal | None:
        with self._sf() as session:
            row = (
                session.query(ChangeProposalRow).filter(ChangeProposalRow.run_id == run_id).first()
            )
            return row.to_domain() if row is not None else None

    def list_for_workspace(self, workspace_id: UUID) -> Sequence[ChangeProposal]:
        with self._sf() as session:
            rows = (
                session.query(ChangeProposalRow)
                .filter(ChangeProposalRow.workspace_id == workspace_id)
                .order_by(ChangeProposalRow.created_at, ChangeProposalRow.id)
                .all()
            )
            return tuple(row.to_domain() for row in rows)

    def replace_if_status(
        self,
        proposal: ChangeProposal,
        expected_status: ChangeProposalStatus,
    ) -> bool:
        with self._sf() as session:
            row = session.get(ChangeProposalRow, proposal.id)
            if row is None or ChangeProposalStatus(row.status) is not expected_status:
                return False
            row.status = proposal.status.value
            row.reviewed_at = proposal.reviewed_at
            row.summary = proposal.summary
            row.rationale = proposal.rationale
            row._file_changes = [
                fc.model_dump(by_alias=False, mode="json") for fc in proposal.file_changes
            ]
            session.commit()
            return True
