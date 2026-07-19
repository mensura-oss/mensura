import os
import signal
import subprocess
from collections.abc import Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from threading import Event, Thread
from time import perf_counter
from typing import BinaryIO, Protocol

OUTPUT_LIMIT_BYTES = 8 * 1024


@dataclass(frozen=True, slots=True)
class CommandExecution:
    exit_code: int | None
    duration_ms: int
    stdout: str
    stderr: str
    output_truncated: bool
    timed_out: bool


class CommandStartError(Exception):
    """Raised when the configured process cannot be started."""


class GuardCommandRunner(Protocol):
    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandExecution: ...


class _BoundedCapture:
    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._data = bytearray()
        self._stopped = Event()
        self.truncated = False

    def drain(self, stream: BinaryIO) -> None:
        while not self._stopped.is_set() and (chunk := stream.read(4096)):
            if self._stopped.is_set():
                return
            remaining = self._limit - len(self._data)
            if remaining > 0:
                self._data.extend(chunk[:remaining])
            if len(chunk) > remaining:
                self.truncated = True

    def stop(self) -> None:
        self.truncated = True
        self._stopped.set()

    def text(self) -> str:
        return self._data.decode("utf-8", errors="replace")


class SubprocessGuardCommandRunner:
    """Run one configured argv without a shell and with bounded output capture."""

    def __init__(self, *, output_limit_bytes: int = OUTPUT_LIMIT_BYTES) -> None:
        self._output_limit_bytes = output_limit_bytes

    def run(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        timeout_seconds: float,
    ) -> CommandExecution:
        started = perf_counter()
        popen_options: dict[str, object] = {
            "cwd": cwd,
            "env": self._environment(),
            "stdout": subprocess.PIPE,
            "stderr": subprocess.PIPE,
        }
        if os.name == "posix":
            popen_options["start_new_session"] = True
        elif os.name == "nt":
            popen_options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            process = subprocess.Popen(list(command), **popen_options)
        except OSError as error:
            raise CommandStartError(str(error)) from error

        assert process.stdout is not None
        assert process.stderr is not None
        stdout_capture = _BoundedCapture(self._output_limit_bytes)
        stderr_capture = _BoundedCapture(self._output_limit_bytes)
        stdout_thread = Thread(target=stdout_capture.drain, args=(process.stdout,), daemon=True)
        stderr_thread = Thread(target=stderr_capture.drain, args=(process.stderr,), daemon=True)
        stdout_thread.start()
        stderr_thread.start()

        timed_out = False
        try:
            process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            self._terminate(process)

        self._finish_output_capture(
            process,
            ((stdout_thread, stdout_capture), (stderr_thread, stderr_capture)),
        )
        duration_ms = max(0, round((perf_counter() - started) * 1000))
        return CommandExecution(
            exit_code=None if timed_out else process.returncode,
            duration_ms=duration_ms,
            stdout=stdout_capture.text(),
            stderr=stderr_capture.text(),
            output_truncated=stdout_capture.truncated or stderr_capture.truncated,
            timed_out=timed_out,
        )

    def _terminate(self, process: subprocess.Popen[bytes]) -> None:
        if process.poll() is not None:
            return
        if os.name == "posix":
            try:
                os.killpg(process.pid, signal.SIGTERM)
                process.wait(timeout=0.5)
                return
            except (ProcessLookupError, subprocess.TimeoutExpired):
                with suppress(ProcessLookupError):
                    os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()

    def _finish_output_capture(
        self,
        process: subprocess.Popen[bytes],
        readers: tuple[tuple[Thread, _BoundedCapture], ...],
    ) -> None:
        for thread, _capture in readers:
            thread.join(timeout=0.1)

        if os.name == "posix" and any(thread.is_alive() for thread, _ in readers):
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGTERM)
            for thread, _capture in readers:
                thread.join(timeout=0.5)

        if os.name == "posix" and any(thread.is_alive() for thread, _ in readers):
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)
            for thread, _capture in readers:
                thread.join(timeout=0.5)

        for thread, capture in readers:
            if thread.is_alive():
                capture.stop()

        assert process.stdout is not None
        assert process.stderr is not None
        if not readers[0][0].is_alive():
            process.stdout.close()
        if not readers[1][0].is_alive():
            process.stderr.close()

    def _environment(self) -> dict[str, str]:
        allowed = {
            "HOME",
            "LANG",
            "LC_ALL",
            "PATH",
            "PATHEXT",
            "SYSTEMROOT",
            "TEMP",
            "TMP",
            "TMPDIR",
            "WINDIR",
        }
        environment = {key: value for key, value in os.environ.items() if key in allowed}
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        environment["PYTHONUNBUFFERED"] = "1"
        environment["PYTEST_DISABLE_PLUGIN_AUTOLOAD"] = "1"
        return environment
