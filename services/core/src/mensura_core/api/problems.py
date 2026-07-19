import logging
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict
from starlette.exceptions import HTTPException as StarletteHTTPException

from mensura_core.exceptions import ResourceConflictError, ResourceNotFoundError

logger = logging.getLogger(__name__)

PROBLEM_MEDIA_TYPE = "application/problem+json"
NOT_FOUND_TYPE = "urn:mensura:problem:resource-not-found"
CONFLICT_TYPE = "urn:mensura:problem:resource-conflict"
VALIDATION_TYPE = "urn:mensura:problem:validation-error"


class InvalidParameter(BaseModel):
    detail: str
    pointer: str


class ProblemDetails(BaseModel):
    model_config = ConfigDict(extra="allow")

    type: str
    title: str
    status: int
    detail: str
    instance: str
    errors: list[InvalidParameter] | None = None


def _problem_response(
    request: Request,
    *,
    status: int,
    problem_type: str,
    title: str,
    detail: str,
    errors: list[InvalidParameter] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    problem = ProblemDetails(
        type=problem_type,
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        errors=errors,
    )
    return JSONResponse(
        status_code=status,
        content=problem.model_dump(mode="json", exclude_none=True),
        headers=headers,
        media_type=PROBLEM_MEDIA_TYPE,
    )


def _json_pointer(location: tuple[Any, ...]) -> str:
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in location]
    return "#/" + "/".join(escaped)


def _status_title(status_code: int) -> str:
    try:
        return HTTPStatus(status_code).phrase
    except ValueError:
        return "HTTP error"


def install_problem_handlers(app: FastAPI) -> None:
    @app.exception_handler(ResourceNotFoundError)
    async def resource_not_found_handler(
        request: Request, error: ResourceNotFoundError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=404,
            problem_type=NOT_FOUND_TYPE,
            title="Resource not found",
            detail=str(error),
        )

    @app.exception_handler(ResourceConflictError)
    async def resource_conflict_handler(
        request: Request, error: ResourceConflictError
    ) -> JSONResponse:
        return _problem_response(
            request,
            status=409,
            problem_type=CONFLICT_TYPE,
            title="Resource conflict",
            detail=error.detail,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, error: RequestValidationError
    ) -> JSONResponse:
        invalid_parameters = [
            InvalidParameter(detail=item["msg"], pointer=_json_pointer(tuple(item["loc"])))
            for item in error.errors()
        ]
        return _problem_response(
            request,
            status=422,
            problem_type=VALIDATION_TYPE,
            title="Request validation failed",
            detail="One or more request values are invalid.",
            errors=invalid_parameters,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, error: StarletteHTTPException
    ) -> JSONResponse:
        status = error.status_code
        title = _status_title(status)
        detail = error.detail if isinstance(error.detail, str) else title
        return _problem_response(
            request,
            status=status,
            problem_type="about:blank",
            title=title,
            detail=detail,
            headers=error.headers,
        )

    @app.exception_handler(Exception)
    async def unexpected_exception_handler(request: Request, error: Exception) -> JSONResponse:
        logger.exception("Unhandled Core API error", exc_info=error)
        return _problem_response(
            request,
            status=500,
            problem_type="about:blank",
            title="Internal Server Error",
            detail="The server could not complete the request.",
        )


def problem_response(status: int, description: str) -> dict[int, dict[str, Any]]:
    return {
        status: {
            "description": description,
            "content": {
                PROBLEM_MEDIA_TYPE: {
                    "schema": ProblemDetails.model_json_schema(mode="serialization")
                }
            },
        }
    }


NOT_FOUND_RESPONSE = problem_response(404, "The requested resource does not exist.")
CONFLICT_RESPONSE = problem_response(409, "The resource conflicts with existing state.")
VALIDATION_RESPONSE = problem_response(422, "The request does not satisfy the v1 contract.")
