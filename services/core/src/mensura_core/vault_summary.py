"""Heuristic architecture summary derived purely from indexed Vault memory items.

Deliberately not AI-generated: it counts and groups indexed metadata and matches a small
table of marker files. Honest and deterministic, a useful first orientation for a repo.
"""

from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from pathlib import PurePosixPath
from uuid import UUID

from mensura_core.vault_index_models import (
    VaultArchitectureSummary,
    VaultModuleSummary,
    VaultSourceType,
)
from mensura_core.vault_index_repositories import VaultItemSummary
from mensura_core.vault_models import VaultNamedCount

MAX_LANGUAGES = 32
MAX_MODULES = 50
MAX_TECHNOLOGIES = 32
MAX_ENTRY_POINTS = 32
ROOT_MODULE_NAME = "(root)"

TECHNOLOGY_BY_FILENAME: dict[str, str] = {
    "package.json": "Node.js",
    "tsconfig.json": "TypeScript",
    "pnpm-workspace.yaml": "pnpm",
    "pyproject.toml": "Python",
    "setup.py": "Python",
    "setup.cfg": "Python",
    "requirements.txt": "Python",
    "pipfile": "Python",
    "cargo.toml": "Rust",
    "go.mod": "Go",
    "dockerfile": "Docker",
    "docker-compose.yml": "Docker Compose",
    "docker-compose.yaml": "Docker Compose",
    "pom.xml": "Maven (JVM)",
    "build.gradle": "Gradle (JVM)",
    "build.gradle.kts": "Gradle (JVM)",
    "gemfile": "Ruby",
    "composer.json": "PHP",
    "makefile": "Make",
    "alembic.ini": "Alembic",
    ".pre-commit-config.yaml": "pre-commit",
}

TECHNOLOGY_BY_SUFFIX: dict[str, str] = {
    ".tf": "Terraform",
}

ENTRY_POINT_FILENAMES = frozenset(
    {
        "main.py",
        "__main__.py",
        "app.py",
        "cli.py",
        "manage.py",
        "wsgi.py",
        "asgi.py",
        "index.ts",
        "index.tsx",
        "index.js",
        "main.ts",
        "main.tsx",
        "main.js",
        "main.rs",
        "main.go",
        "mod.rs",
        "server.ts",
        "server.js",
    }
)


def _module_name(path: str) -> tuple[str, str]:
    parts = PurePosixPath(path).parts
    if len(parts) <= 1:
        return ROOT_MODULE_NAME, ""
    return parts[0], parts[0]


def _named_counts(counts: Counter[str], limit: int) -> list[VaultNamedCount]:
    ordered = sorted(counts.items(), key=lambda pair: (-pair[1], pair[0]))
    return [VaultNamedCount(value=value, count=count) for value, count in ordered[:limit]]


def summarize_architecture(
    items: Sequence[VaultItemSummary],
    *,
    workspace_id: UUID,
    index_id: UUID,
    generated_at: datetime,
) -> VaultArchitectureSummary:
    language_counts: Counter[str] = Counter()
    technologies: set[str] = set()
    entry_points: set[str] = set()

    module_files: Counter[str] = Counter()
    module_paths: dict[str, str] = {}
    module_bytes: dict[str, int] = {}
    module_languages: dict[str, Counter[str]] = {}

    for item in items:
        if item.language:
            language_counts[item.language] += 1

        name, module_path = _module_name(item.path)
        module_files[name] += 1
        module_paths[name] = module_path
        module_bytes[name] = module_bytes.get(name, 0) + item.size_bytes
        if item.language:
            module_languages.setdefault(name, Counter())[item.language] += 1

        basename = PurePosixPath(item.path).name.casefold()
        if basename in TECHNOLOGY_BY_FILENAME:
            technologies.add(TECHNOLOGY_BY_FILENAME[basename])
        suffix = PurePosixPath(item.path).suffix.casefold()
        if suffix in TECHNOLOGY_BY_SUFFIX:
            technologies.add(TECHNOLOGY_BY_SUFFIX[suffix])
        if basename in ENTRY_POINT_FILENAMES:
            entry_points.add(item.path)

    modules = [
        VaultModuleSummary(
            name=name,
            path=module_paths[name],
            file_count=count,
            total_size_bytes=module_bytes[name],
            primary_language=(
                module_languages[name].most_common(1)[0][0] if module_languages.get(name) else None
            ),
        )
        for name, count in sorted(module_files.items(), key=lambda pair: (-pair[1], pair[0]))
    ][:MAX_MODULES]

    return VaultArchitectureSummary(
        workspace_id=workspace_id,
        index_id=index_id,
        generated_at=generated_at,
        file_count=len(items),
        code_file_count=sum(1 for item in items if item.source_type is VaultSourceType.CODE),
        doc_file_count=sum(1 for item in items if item.source_type is VaultSourceType.DOC),
        config_file_count=sum(1 for item in items if item.source_type is VaultSourceType.CONFIG),
        total_size_bytes=sum(item.size_bytes for item in items),
        languages=_named_counts(language_counts, MAX_LANGUAGES),
        modules=modules,
        technologies=sorted(technologies)[:MAX_TECHNOLOGIES],
        entry_points=sorted(entry_points)[:MAX_ENTRY_POINTS],
    )
