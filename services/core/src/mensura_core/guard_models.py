from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AwareDatetime, Field, StringConstraints, field_validator

from mensura_core.models import ApiModel, ResourceModel

CommandToken = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
CompactOutput = Annotated[str, StringConstraints(max_length=8192)]


class GuardCheckKind(StrEnum):
    LINT = "lint"
    TEST = "test"


class GuardCheckStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"


class GuardRunStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"


class GuardRunCreate(ApiModel):
    checks: Annotated[list[GuardCheckKind] | None, Field(min_length=1, max_length=2)] = None

    @field_validator("checks")
    @classmethod
    def checks_must_be_unique(
        cls, checks: list[GuardCheckKind] | None
    ) -> list[GuardCheckKind] | None:
        if checks is not None and len(checks) != len(set(checks)):
            raise ValueError("Guard checks must not contain duplicates")
        return checks


class GuardCommandConfiguration(ResourceModel):
    command: Annotated[list[CommandToken], Field(min_length=1, max_length=64)]
    blocking: bool = True

    @field_validator("command")
    @classmethod
    def command_tokens_must_be_safe(cls, command: list[str]) -> list[str]:
        if any(
            not token.strip() or "\0" in token or "\n" in token or "\r" in token
            for token in command
        ):
            raise ValueError("Command tokens must be non-empty single-line values")
        return command


class GuardChecksConfiguration(ResourceModel):
    lint: GuardCommandConfiguration
    test: GuardCommandConfiguration


class GuardConfiguration(ResourceModel):
    version: Literal[1]
    timeout_seconds: Annotated[int, Field(ge=1, le=300)] = 120
    checks: GuardChecksConfiguration


class GuardCheckResult(ResourceModel):
    kind: GuardCheckKind
    status: GuardCheckStatus
    blocking: bool
    summary: Annotated[str, StringConstraints(min_length=1, max_length=240)]
    command: Annotated[list[CommandToken], Field(min_length=1, max_length=64)]
    exit_code: int | None
    duration_ms: Annotated[int, Field(ge=0)]
    stdout: CompactOutput
    stderr: CompactOutput
    output_truncated: bool


class GuardSummary(ResourceModel):
    total_count: Annotated[int, Field(ge=0)]
    passed_count: Annotated[int, Field(ge=0)]
    failed_count: Annotated[int, Field(ge=0)]
    error_count: Annotated[int, Field(ge=0)]
    blocking_failures: Annotated[int, Field(ge=0)]
    is_blocking: bool


class GuardRunResponse(ResourceModel):
    id: UUID
    workspace_id: UUID
    status: GuardRunStatus
    blocking: bool
    summary: GuardSummary
    checks: Annotated[list[GuardCheckResult], Field(min_length=1, max_length=2)]
    started_at: AwareDatetime
    completed_at: AwareDatetime
    duration_ms: Annotated[int, Field(ge=0)]
