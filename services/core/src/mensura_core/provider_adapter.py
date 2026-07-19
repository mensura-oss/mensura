from typing import Protocol

from mensura_core.context_pack_models import ContextPackManifest
from mensura_core.models import (
    ChangeProposalDraft,
    PromptVersion,
    ProviderId,
    ProviderKind,
    ResourceModel,
    RunExecutionContextSummary,
    RunExecutionResult,
    RunProviderMetadata,
    Task,
)


class ProviderExecutionRequest(ResourceModel):
    """Bounded provider input with no live repository or workspace-path capability."""

    task: Task
    context_pack: ContextPackManifest


class ProviderAdapter(Protocol):
    @property
    def identity(self) -> RunProviderMetadata: ...

    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult: ...


class ProviderAdapterExecutionError(Exception):
    """Expected adapter failure whose internal details must not cross the API."""


class ProviderCredentialsRejectedError(ProviderAdapterExecutionError):
    """The upstream provider rejected the locally configured credential."""


class ProviderUpstreamError(ProviderAdapterExecutionError):
    """The upstream provider failed or returned an unusable transport response."""


class ProviderStructuredOutputError(ProviderAdapterExecutionError):
    """The upstream payload did not satisfy the locally enforced result contract."""


class DeterministicReviewProvider:
    """Credential-free metadata review adapter for the first execution boundary."""

    _identity = RunProviderMetadata(
        provider_id=ProviderId.DETERMINISTIC,
        provider_kind=ProviderKind.DETERMINISTIC,
        adapter_id="deterministic-review",
        adapter_version="1.0.0",
        model=None,
        prompt_version=PromptVersion.REVIEW_V2,
    )

    @property
    def identity(self) -> RunProviderMetadata:
        return self._identity

    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        task = request.task
        manifest = request.context_pack
        summary = manifest.summary
        task_summary = task.title
        if task.description:
            task_summary = f"{task.title}: {task.description}"[:1000]

        warnings: list[str] = []
        if not task.description:
            warnings.append("The task has no description; intent is derived from its title only.")
        if summary.binary_file_count:
            warnings.append(
                f"{summary.binary_file_count} context file(s) are metadata-only binary evidence."
            )
        if summary.truncated_text_file_count:
            warnings.append(
                f"{summary.truncated_text_file_count} text preview(s) are intentionally truncated."
            )

        return RunExecutionResult(
            task_summary=task_summary,
            interpreted_intent=task.description or task.title,
            context=execution_context_summary(manifest),
            warnings=tuple(warnings),
            recommended_next_steps=(
                "Review this bounded result against the immutable context before continuing.",
                "Materialize the write-isolated proposal artifact before any review decision.",
            ),
            proposal_draft=ChangeProposalDraft(
                summary="No file changes proposed by the deterministic review provider.",
                rationale=(
                    "The built-in provider verifies context lineage and execution boundaries but "
                    "does not synthesize code changes."
                ),
                file_changes=(),
            ),
        )


def execution_context_summary(manifest: ContextPackManifest) -> RunExecutionContextSummary:
    summary = manifest.summary
    languages = tuple(
        sorted({entry.language for entry in manifest.files if entry.language is not None})
    )
    return RunExecutionContextSummary(
        context_pack_id=manifest.id,
        inventory_id=manifest.inventory_id,
        file_count=summary.file_count,
        text_file_count=summary.text_file_count,
        binary_file_count=summary.binary_file_count,
        total_file_bytes=summary.total_file_bytes,
        total_preview_bytes=summary.total_preview_bytes,
        truncated_text_file_count=summary.truncated_text_file_count,
        languages=languages,
    )
