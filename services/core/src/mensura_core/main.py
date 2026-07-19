from fastapi import FastAPI

from mensura_core import __version__
from mensura_core.api.problems import install_problem_handlers
from mensura_core.api.router import router as v1_router
from mensura_core.api.routers.health import router as health_router
from mensura_core.repositories import CoreRepository, InMemoryCoreRepository
from mensura_core.service import CoreService


def create_app(repository: CoreRepository | None = None) -> FastAPI:
    app = FastAPI(
        title="Mensura Core API",
        summary="Versioned task and run boundary for Mensura",
        version=__version__,
        docs_url="/docs",
        openapi_url="/openapi.json",
    )
    app.state.core_service = CoreService(repository or InMemoryCoreRepository())
    install_problem_handlers(app)
    app.include_router(health_router)
    app.include_router(v1_router)
    return app


app = create_app()


def run() -> None:
    import uvicorn

    uvicorn.run("mensura_core.main:app", host="127.0.0.1", port=8000)
