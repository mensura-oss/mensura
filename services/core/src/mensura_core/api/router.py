from fastapi import APIRouter

from mensura_core.api.routers import runs, tasks, workspaces

router = APIRouter(prefix="/api/v1")
router.include_router(workspaces.router)
router.include_router(tasks.router)
router.include_router(runs.router)
