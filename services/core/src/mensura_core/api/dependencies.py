from typing import Annotated, cast

from fastapi import Depends, Request

from mensura_core.guard_service import GuardService
from mensura_core.service import CoreService


def get_core_service(request: Request) -> CoreService:
    return cast(CoreService, request.app.state.core_service)


CoreServiceDependency = Annotated[CoreService, Depends(get_core_service)]


def get_guard_service(request: Request) -> GuardService:
    return cast(GuardService, request.app.state.guard_service)


GuardServiceDependency = Annotated[GuardService, Depends(get_guard_service)]
