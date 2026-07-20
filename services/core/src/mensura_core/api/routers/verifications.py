from uuid import UUID

from fastapi import APIRouter, Response, status

from mensura_core.api.dependencies import ProposalVerificationServiceDependency
from mensura_core.api.problems import (
    NOT_FOUND_RESPONSE,
    VALIDATION_RESPONSE,
    VERIFICATION_CONFLICT_RESPONSE,
    VERIFICATION_SANDBOX_RESPONSE,
    VERIFICATION_UNSUPPORTED_RESPONSE,
)
from mensura_core.verification_models import (
    ProposalVerification,
    ProposalVerificationCollection,
)

router = APIRouter(tags=["proposal-verifications"])


@router.post(
    "/change-proposals/{proposal_id}/verify",
    response_model=ProposalVerification,
    status_code=status.HTTP_201_CREATED,
    responses={
        **NOT_FOUND_RESPONSE,
        **VERIFICATION_CONFLICT_RESPONSE,
        **VERIFICATION_UNSUPPORTED_RESPONSE,
        **VERIFICATION_SANDBOX_RESPONSE,
        **VALIDATION_RESPONSE,
    },
    summary="Verify an approved proposal in a temporary isolated sandbox",
)
def verify_change_proposal(
    proposal_id: UUID,
    response: Response,
    service: ProposalVerificationServiceDependency,
) -> ProposalVerification:
    verification = service.verify(proposal_id)
    response.headers["Location"] = f"/api/v1/verifications/{verification.id}"
    return verification


@router.get(
    "/change-proposals/{proposal_id}/verifications",
    response_model=ProposalVerificationCollection,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="List verification artifacts for a change proposal",
)
async def list_change_proposal_verifications(
    proposal_id: UUID,
    service: ProposalVerificationServiceDependency,
) -> ProposalVerificationCollection:
    return service.list_for_proposal(proposal_id)


@router.get(
    "/verifications/{verification_id}",
    response_model=ProposalVerification,
    responses={**NOT_FOUND_RESPONSE, **VALIDATION_RESPONSE},
    summary="Get a proposal verification artifact",
)
async def get_change_proposal_verification(
    verification_id: UUID,
    service: ProposalVerificationServiceDependency,
) -> ProposalVerification:
    return service.get(verification_id)
