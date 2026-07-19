import json
import re
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from mensura_core.exceptions import (
    GuardConfigurationInvalidError,
    GuardConfigurationNotFoundError,
    UnsupportedWorkspaceStateError,
)
from mensura_core.guard_models import GuardCheckKind, GuardConfiguration

CONFIG_RELATIVE_PATH = Path(".mensura/guard.json")
MAX_CONFIG_BYTES = 64 * 1024
PYTHON_EXECUTABLE = re.compile(r"python(?:3(?:\.\d+)?)?(?:\.exe)?", re.IGNORECASE)


class GuardConfigurationLoader(Protocol):
    def load(self, workspace_root: str) -> GuardConfiguration: ...


class JsonGuardConfigurationLoader:
    """Load a strict repository-local Guard v1 configuration."""

    def load(self, workspace_root: str) -> GuardConfiguration:
        root = Path(workspace_root)
        if not root.exists() or not root.is_dir():
            raise UnsupportedWorkspaceStateError(
                f"Workspace root path '{workspace_root}' does not exist or is not a directory."
            )

        config_path = root / CONFIG_RELATIVE_PATH
        if not config_path.exists() or not config_path.is_file():
            raise GuardConfigurationNotFoundError(str(config_path))

        try:
            resolved_root = root.resolve(strict=True)
            resolved_config = config_path.resolve(strict=True)
        except OSError as error:
            raise GuardConfigurationInvalidError(
                str(config_path), "The configuration path cannot be resolved."
            ) from error

        if not resolved_config.is_relative_to(resolved_root):
            raise GuardConfigurationInvalidError(
                str(config_path), "The configuration must stay inside the workspace root."
            )

        try:
            if resolved_config.stat().st_size > MAX_CONFIG_BYTES:
                raise GuardConfigurationInvalidError(
                    str(config_path), "The configuration exceeds 64 KiB."
                )
            raw_config = json.loads(resolved_config.read_text(encoding="utf-8"))
            configuration = GuardConfiguration.model_validate(raw_config)
        except GuardConfigurationInvalidError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError, ValidationError) as error:
            raise GuardConfigurationInvalidError(
                str(config_path), "The configuration is not valid Guard v1 JSON."
            ) from error

        self._validate_tool(GuardCheckKind.LINT, configuration.checks.lint.command, config_path)
        self._validate_tool(GuardCheckKind.TEST, configuration.checks.test.command, config_path)
        return configuration

    def _validate_tool(self, kind: GuardCheckKind, command: list[str], config_path: Path) -> None:
        executable = Path(command[0]).name.lower()
        arguments = command[1:]
        tool: str | None = None

        if executable in {"ruff", "ruff.exe"}:
            tool = "ruff"
        elif executable in {"pytest", "pytest.exe"}:
            tool = "pytest"
        elif (
            PYTHON_EXECUTABLE.fullmatch(executable) and len(arguments) >= 2 and arguments[0] == "-m"
        ):
            tool = arguments[1]

        expected_tool = "ruff" if kind is GuardCheckKind.LINT else "pytest"
        if tool != expected_tool:
            raise GuardConfigurationInvalidError(
                str(config_path),
                f"The {kind.value} check must invoke {expected_tool} "
                "directly or through python -m.",
            )
