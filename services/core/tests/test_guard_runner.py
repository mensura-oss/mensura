import sys
from pathlib import Path

import pytest

from mensura_core.guard_runner import CommandStartError, SubprocessGuardCommandRunner


def test_runner_captures_cwd_exit_and_both_streams(tmp_path: Path) -> None:
    runner = SubprocessGuardCommandRunner()

    execution = runner.run(
        [
            sys.executable,
            "-c",
            "import pathlib, sys; print(pathlib.Path.cwd()); print('warning', file=sys.stderr)",
        ],
        cwd=tmp_path,
        timeout_seconds=2,
    )

    assert execution.exit_code == 0
    assert execution.timed_out is False
    assert execution.stdout.strip() == str(tmp_path)
    assert execution.stderr.strip() == "warning"
    assert execution.duration_ms >= 0
    assert execution.output_truncated is False


def test_runner_bounds_output_while_draining_the_process(tmp_path: Path) -> None:
    runner = SubprocessGuardCommandRunner(output_limit_bytes=32)

    execution = runner.run(
        [
            sys.executable,
            "-c",
            "import sys; print('a' * 1000); print('b' * 1000, file=sys.stderr)",
        ],
        cwd=tmp_path,
        timeout_seconds=2,
    )

    assert execution.exit_code == 0
    assert len(execution.stdout.encode()) <= 32
    assert len(execution.stderr.encode()) <= 32
    assert execution.output_truncated is True


def test_runner_normalizes_timeout_as_a_completed_execution(tmp_path: Path) -> None:
    runner = SubprocessGuardCommandRunner()

    execution = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        cwd=tmp_path,
        timeout_seconds=0.05,
    )

    assert execution.exit_code is None
    assert execution.timed_out is True
    assert execution.duration_ms < 2000


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX process-group behavior")
def test_runner_reaps_descendants_that_inherit_output_pipes(tmp_path: Path) -> None:
    runner = SubprocessGuardCommandRunner()

    execution = runner.run(
        [
            sys.executable,
            "-c",
            (
                "import subprocess, sys; "
                "subprocess.Popen([sys.executable, '-c', "
                "'import time; time.sleep(10)']); "
                "print('parent done')"
            ),
        ],
        cwd=tmp_path,
        timeout_seconds=2,
    )

    assert execution.exit_code == 0
    assert execution.stdout.strip() == "parent done"
    assert execution.duration_ms < 2000


def test_runner_reports_process_start_failure(tmp_path: Path) -> None:
    with pytest.raises(CommandStartError):
        SubprocessGuardCommandRunner().run(
            [str(tmp_path / "missing-command")],
            cwd=tmp_path,
            timeout_seconds=1,
        )
