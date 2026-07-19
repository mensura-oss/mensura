from uuid import UUID

from fastapi import APIRouter, Response, status

from mensura_core.api.dependencies import ChangeProposalServiceDependency
from mensura_core.api.problems import (
    CHANGE_PROPOSAL_CONFLICT_RESPONSE,
    CHANGE_PROPOSAL_INVALID_RESPONSE,
    CHANGE_PROPOSAL_TOO_LARGE_RESPONSE,
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
)
from mensura_core.change_proposal_models import (
    ChangeProposal,
    ChangeProposalCollection,
    CreateChangeProposalResponse,
)

router = APIRouter(tags=["change-proposals"])


@router.post(
    "/runs/{run_id}/change-proposals",
    response_model=CreateChangeProposalResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **CHANGE_PROPOSAL_CONFLICT_RESPONSE,
        **CHANGE_PROPOSAL_INVALID_RESPONSE,
        **CHANGE_PROPOSAL_TOO_LARGE_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Create an idempotent write-isolated proposal from a successful run",
)
def create_change_proposal(
    run_id: UUID,
    response: Response,
    service: ChangeProposalServiceDependency,
) -> CreateChangeProposalResponse:
    result = service.create(run_id)
    response.headers["Location"] = f"/api/v1/change-proposals/{result.proposal.id}"
    return result


@router.get(
    "/change-proposals/{proposal_id}",
    response_model=ChangeProposal,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a change proposal",
)
async def get_change_proposal(
    proposal_id: UUID,
    service: ChangeProposalServiceDependency,
) -> ChangeProposal:
    return service.get(proposal_id)


@router.get(
    "/workspaces/{workspace_id}/change-proposals",
    response_model=ChangeProposalCollection,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="List change proposals for a workspace",
)
async def list_change_proposals(
    workspace_id: UUID,
    service: ChangeProposalServiceDependency,
) -> ChangeProposalCollection:
    return service.list_for_workspace(workspace_id)


@router.post(
    "/change-proposals/{proposal_id}/approve",
    response_model=ChangeProposal,
    responses={
        **NOT_FOUND_RESPONSE,
        **CHANGE_PROPOSAL_CONFLICT_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Approve a proposed artifact without applying it",
)
def approve_change_proposal(
    proposal_id: UUID,
    service: ChangeProposalServiceDependency,
) -> ChangeProposal:
    return service.approve(proposal_id)


@router.post(
    "/change-proposals/{proposal_id}/reject",
    response_model=ChangeProposal,
    responses={
        **NOT_FOUND_RESPONSE,
        **CHANGE_PROPOSAL_CONFLICT_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Reject a proposed artifact without applying it",
)
def reject_change_proposal(
    proposal_id: UUID,
    service: ChangeProposalServiceDependency,
) -> ChangeProposal:
    return service.reject(proposal_id)
