import json
from dataclasses import dataclass

from mensura_core.models import PromptVersion
from mensura_core.provider_adapter import ProviderExecutionRequest


@dataclass(frozen=True)
class PromptMapping:
    version: PromptVersion
    instructions: str

    def render_input(self, request: ProviderExecutionRequest) -> str:
        payload = {
            "task": request.task.model_dump(mode="json", by_alias=True),
            "contextPack": request.context_pack.model_dump(mode="json", by_alias=True),
        }
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


REVIEW_V1 = PromptMapping(
    version=PromptVersion.REVIEW_V1,
    instructions=(
        "You are Mensura's read-only review adapter. Analyze only the supplied persisted task "
        "and immutable context pack. Do not claim to read live files, use tools, execute commands, "
        "or change a repository. Return a compact structured review. Keep every statement grounded "
        "in the supplied evidence, call out missing or truncated evidence as a warning, and "
        "propose review-oriented next steps rather than file modifications."
    ),
)

REVIEW_V2 = PromptMapping(
    version=PromptVersion.REVIEW_V2,
    instructions=(
        "You are Mensura's write-isolated proposal adapter. Analyze only the supplied persisted "
        "task and immutable context pack. Do not claim to read live files, use tools, execute "
        "commands, or change a repository. Return a compact structured review plus a bounded "
        "proposal draft. Every modify/delete path must exist in the supplied context pack; create "
        "paths must be normalized relative paths. Propose text only for text files, use null text "
        "for deletes, and keep every suggestion grounded in captured evidence. An empty "
        "fileChanges array is valid when the evidence is insufficient."
    ),
)

PROMPT_MAPPINGS: dict[PromptVersion, PromptMapping] = {
    PromptVersion.REVIEW_V1: REVIEW_V1,
    PromptVersion.REVIEW_V2: REVIEW_V2,
}


def get_prompt_mapping(version: PromptVersion) -> PromptMapping:
    return PROMPT_MAPPINGS[version]
