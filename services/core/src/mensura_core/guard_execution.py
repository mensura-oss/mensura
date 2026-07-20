"""Shared bounded Guard check execution used by Guard runs and proposal verification."""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from mensura_core.exceptions import GuardExecutionError
from mensura_core.guard_config import GuardConfigurationLoader
from mensura_core.guard_models import (
    GuardCheckKind,
    GuardCheckResult,
    GuardCheckStatus,
    GuardCommandConfiguration,
    GuardRunStatus,
    GuardSummary,
)
from mensura_core.guard_runner import CommandExecution, CommandStartError, GuardCommandRunner
from mensura_core.models import ensure_utc_timestamp

Clock = Callable[[], datetime]
Monotonic = Callable[[], float]


@dataclass(frozen=True, slots=True)
class GuardChecksExecution:
    status: GuardRunStatus
    summary: GuardSummary
    checks: list[GuardCheckResult]
    started_at: datetime
    completed_at: datetime
    duration_ms: int


def execute_guard_checks(
    root: str,
    requested_checks: Sequence[GuardCheckKind],
    *,
    configuration_loader: GuardConfigurationLoader,
    command_runner: GuardCommandRunner,
    clock: Clock,
    monotonic: Monotonic,
) -> GuardChecksExecution:
    configuration = configuration_loader.load(root)
    started_at = ensure_utc_timestamp(clock())
    started = monotonic()
    results: list[GuardCheckResult] = []

    for kind in requested_checks:
        check_config = getattr(configuration.checks, kind.value)
        try:
            execution = command_runner.run(
                check_config.command,
                cwd=Path(root),
                timeout_seconds=configuration.timeout_seconds,
            )
        except CommandStartError as error:
            raise GuardExecutionError(kind.value) from error
        results.append(_normalize(kind, check_config, execution, configuration.timeout_seconds))

    completed_at = ensure_utc_timestamp(clock())
    blocking_failures = sum(
        result.blocking and result.status is not GuardCheckStatus.PASSED for result in results
    )
    passed_count = sum(result.status is GuardCheckStatus.PASSED for result in results)
    summary = GuardSummary(
        total_count=len(results),
        passed_count=passed_count,
        failed_count=sum(result.status is GuardCheckStatus.FAILED for result in results),
        error_count=sum(result.status is GuardCheckStatus.ERROR for result in results),
        blocking_failures=blocking_failures,
        is_blocking=blocking_failures > 0,
    )
    return GuardChecksExecution(
        status=(GuardRunStatus.PASSED if passed_count == len(results) else GuardRunStatus.FAILED),
        summary=summary,
        checks=results,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=max(0, round((monotonic() - started) * 1000)),
    )


def _normalize(
    kind: GuardCheckKind,
    configuration: GuardCommandConfiguration,
    execution: CommandExecution,
    timeout_seconds: int,
) -> GuardCheckResult:
    if execution.timed_out:
        status = GuardCheckStatus.ERROR
        summary = f"{_label(kind)} timed out after {timeout_seconds} seconds."
    elif execution.exit_code == 0:
        status = GuardCheckStatus.PASSED
        summary = f"{_label(kind)} passed."
    else:
        status = GuardCheckStatus.FAILED
        summary = _failure_summary(kind, execution)

    return GuardCheckResult(
        kind=kind,
        status=status,
        blocking=configuration.blocking,
        summary=summary,
        command=configuration.command,
        exit_code=execution.exit_code,
        duration_ms=execution.duration_ms,
        stdout=execution.stdout,
        stderr=execution.stderr,
        output_truncated=execution.output_truncated,
    )


def _failure_summary(kind: GuardCheckKind, execution: CommandExecution) -> str:
    if kind is GuardCheckKind.LINT:
        try:
            diagnostics = json.loads(execution.stdout)
        except json.JSONDecodeError:
            diagnostics = None
        if isinstance(diagnostics, list):
            count = len(diagnostics)
            noun = "diagnostic" if count == 1 else "diagnostics"
            return f"Lint failed with {count} {noun}."
    return f"{_label(kind)} failed with exit code {execution.exit_code}."


def _label(kind: GuardCheckKind) -> str:
    return "Lint" if kind is GuardCheckKind.LINT else "Tests"
