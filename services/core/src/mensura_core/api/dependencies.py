from typing import Annotated, cast

from fastapi import Depends, Request

from mensura_core.service import CoreService


def get_core_service(request: Request) -> CoreService:
    return cast(CoreService, request.app.state.core_service)


CoreServiceDependency = Annotated[CoreService, Depends(get_core_service)]
