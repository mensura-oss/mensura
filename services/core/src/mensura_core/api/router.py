from fastapi import APIRouter

from mensura_core.api.routers import (
    applications,
    change_proposals,
    context_packs,
    guard,
    providers,
    runs,
    tasks,
    vault,
    verifications,
    workspaces,
)

router = APIRouter(prefix="/api/v1")
router.include_router(workspaces.router)
router.include_router(tasks.router)
router.include_router(runs.router)
router.include_router(providers.router)
router.include_router(guard.router)
router.include_router(vault.router)
router.include_router(context_packs.router)
router.include_router(change_proposals.router)
router.include_router(verifications.router)
router.include_router(applications.router)
