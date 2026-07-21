from fastapi import APIRouter

from mensura_core.api.routers import (
    applications,
    backups,
    change_proposals,
    context_packs,
    events,
    guard,
    jobs,
    providers,
    runs,
    tasks,
    undos,
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
router.include_router(undos.router)
router.include_router(backups.router)
router.include_router(jobs.router)
router.include_router(events.router)
