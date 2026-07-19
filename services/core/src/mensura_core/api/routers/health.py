from fastapi import APIRouter

from mensura_core import __version__
from mensura_core.models import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse, summary="Check Core liveness")
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="mensura-core", version=__version__)
