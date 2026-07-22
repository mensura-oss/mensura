"""Minimal, conservative retention policy for operational byproducts.

Retention here is *best-effort local hygiene* for the two artifacts that otherwise grow
without bound during long-term single-user use — database **backups** and **terminal
jobs**. It is deliberately **not** a replacement for an external backup strategy, and it
is never applied to core domain artifacts (tasks, proposals, verifications, applications,
undos) or to queued/running jobs.

A single :class:`RetentionPolicy` governs both. An item is *kept* if it satisfies **any**
of: it is within ``keep_at_least`` of the newest, it is within the newest ``max_count``,
or it is newer than ``max_age_days``. It is *pruned* only when it fails all three — i.e.
it is both beyond the count limit *and* older than the age limit. Either dimension set to
``0`` is inactive; with **both** ``0`` the policy is disabled and prunes nothing (the
documented off-switch).
"""

import logging
import os
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TypeVar

logger = logging.getLogger(__name__)

# Conservative defaults — favor safety over aggressive cleanup.
DEFAULT_BACKUP_RETENTION_COUNT = 10
DEFAULT_BACKUP_RETENTION_DAYS = 30
DEFAULT_JOB_RETENTION_COUNT = 200
DEFAULT_JOB_RETENTION_DAYS = 30

BACKUP_RETENTION_COUNT_VAR = "MENSURA_BACKUP_RETENTION_COUNT"
BACKUP_RETENTION_DAYS_VAR = "MENSURA_BACKUP_RETENTION_DAYS"
JOB_RETENTION_COUNT_VAR = "MENSURA_JOB_RETENTION_COUNT"
JOB_RETENTION_DAYS_VAR = "MENSURA_JOB_RETENTION_DAYS"

T = TypeVar("T")


def _parse_int(raw: str | None, default: int, *, name: str) -> int:
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError:
        logger.warning("Ignoring invalid value %r for %s; using default %d.", raw, name, default)
        return default


@dataclass(frozen=True)
class RetentionResult:
    """The outcome of a single prune pass, for logging and tests."""

    inspected: int = 0
    deleted: int = 0
    kept: int = 0
    failed: int = 0


@dataclass(frozen=True)
class RetentionPolicy:
    """Union-of-keeps retention with an optional hard safety floor.

    ``max_count`` keeps the newest N; ``max_age_days`` keeps anything newer than N days;
    ``keep_at_least`` unconditionally protects the N newest regardless of the other knobs
    (used to guarantee the newest backup is never pruned).
    """

    max_count: int
    max_age_days: int
    keep_at_least: int = 0

    @property
    def enabled(self) -> bool:
        """With both dimensions inactive the policy prunes nothing."""
        return self.max_count > 0 or self.max_age_days > 0

    def partition(
        self,
        items: Sequence[T],
        *,
        now: datetime,
        timestamp: Callable[[T], datetime],
    ) -> tuple[list[T], list[T]]:
        """Split ``items`` into ``(kept, pruned)``. Order-independent: sorts newest-first."""
        ordered = sorted(items, key=timestamp, reverse=True)
        if not self.enabled:
            return list(ordered), []
        cutoff = now - timedelta(days=self.max_age_days) if self.max_age_days > 0 else None
        kept: list[T] = []
        pruned: list[T] = []
        for index, item in enumerate(ordered):
            keep = (
                index < self.keep_at_least
                or (self.max_count > 0 and index < self.max_count)
                or (cutoff is not None and timestamp(item) >= cutoff)
            )
            (kept if keep else pruned).append(item)
        return kept, pruned

    @classmethod
    def from_env(
        cls,
        *,
        count_var: str,
        days_var: str,
        default_count: int,
        default_days: int,
        keep_at_least: int = 0,
        env: Mapping[str, str] | None = None,
    ) -> "RetentionPolicy":
        source = env if env is not None else os.environ
        count = _parse_int(source.get(count_var), default_count, name=count_var)
        days = _parse_int(source.get(days_var), default_days, name=days_var)
        return cls(
            max_count=max(count, 0),
            max_age_days=max(days, 0),
            keep_at_least=max(keep_at_least, 0),
        )


def backup_retention_from_env(env: Mapping[str, str] | None = None) -> RetentionPolicy:
    """Backup policy. ``keep_at_least=1`` never deletes the user's only/newest backup."""
    return RetentionPolicy.from_env(
        count_var=BACKUP_RETENTION_COUNT_VAR,
        days_var=BACKUP_RETENTION_DAYS_VAR,
        default_count=DEFAULT_BACKUP_RETENTION_COUNT,
        default_days=DEFAULT_BACKUP_RETENTION_DAYS,
        keep_at_least=1,
        env=env,
    )


def job_retention_from_env(env: Mapping[str, str] | None = None) -> RetentionPolicy:
    """Terminal-job policy. Jobs are pure orchestration byproducts, so no hard floor."""
    return RetentionPolicy.from_env(
        count_var=JOB_RETENTION_COUNT_VAR,
        days_var=JOB_RETENTION_DAYS_VAR,
        default_count=DEFAULT_JOB_RETENTION_COUNT,
        default_days=DEFAULT_JOB_RETENTION_DAYS,
        keep_at_least=0,
        env=env,
    )
