import json
from collections.abc import Mapping
from typing import Annotated, Any, Protocol

import httpx
from pydantic import Field, ValidationError

from mensura_core.models import (
    ApiModel,
    BoundedMessage,
    BoundedSummary,
    ChangeProposalDraft,
    PromptVersion,
    ProviderId,
    ProviderKind,
    RunExecutionResult,
    RunProviderMetadata,
)
from mensura_core.provider_adapter import (
    ProviderCredentialsRejectedError,
    ProviderExecutionRequest,
    ProviderStructuredOutputError,
    ProviderUpstreamError,
    execution_context_summary,
)
from mensura_core.provider_prompts import get_prompt_mapping

OPENAI_RESPONSES_URL = "https://api.openai.com/v1/responses"
OPENAI_TIMEOUT_SECONDS = 45.0
OPENAI_MAX_OUTPUT_TOKENS = 1_200


class OpenAIResponseTransport(Protocol):
    def create_response(self, api_key: str, payload: Mapping[str, Any]) -> tuple[int, Any]: ...


class HttpxOpenAIResponseTransport:
    def create_response(self, api_key: str, payload: Mapping[str, Any]) -> tuple[int, Any]:
        try:
            response = httpx.post(
                OPENAI_RESPONSES_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=OPENAI_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as error:
            raise ProviderUpstreamError from error
        try:
            body = response.json()
        except ValueError as error:
            raise ProviderUpstreamError from error
        return response.status_code, body


class OpenAIReviewOutput(ApiModel):
    task_summary: BoundedSummary
    interpreted_intent: BoundedSummary
    warnings: Annotated[tuple[BoundedMessage, ...], Field(max_length=8)]
    recommended_next_steps: Annotated[tuple[BoundedMessage, ...], Field(min_length=1, max_length=8)]
    proposal_draft: ChangeProposalDraft


class OpenAIReviewProvider:
    """Optional real adapter constrained to immutable inputs and bounded JSON output."""

    def __init__(
        self,
        *,
        model: str,
        api_key: str,
        transport: OpenAIResponseTransport | None = None,
        prompt_version: PromptVersion = PromptVersion.REVIEW_V2,
    ) -> None:
        self._api_key = api_key
        self._transport = transport or HttpxOpenAIResponseTransport()
        self._prompt_version = prompt_version
        self._identity = RunProviderMetadata(
            provider_id=ProviderId.OPENAI,
            provider_kind=ProviderKind.REAL,
            adapter_id="openai-responses",
            adapter_version="1.0.0",
            model=model,
            prompt_version=prompt_version,
        )

    @property
    def identity(self) -> RunProviderMetadata:
        return self._identity

    def execute(self, request: ProviderExecutionRequest) -> RunExecutionResult:
        prompt = get_prompt_mapping(self._prompt_version)
        status_code, body = self._transport.create_response(
            self._api_key,
            {
                "model": self._identity.model,
                "instructions": prompt.instructions,
                "input": [
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": prompt.render_input(request)}],
                    }
                ],
                "text": {
                    "format": {
                        "type": "json_schema",
                        "name": "mensura_review_v2",
                        "description": (
                            "A bounded read-only review and write-isolated proposal draft from "
                            "immutable Mensura context."
                        ),
                        "strict": True,
                        "schema": _review_output_schema(),
                    }
                },
                "max_output_tokens": OPENAI_MAX_OUTPUT_TOKENS,
                "store": False,
                "truncation": "disabled",
            },
        )
        if status_code in {401, 403}:
            raise ProviderCredentialsRejectedError
        if status_code < 200 or status_code >= 300:
            raise ProviderUpstreamError

        output_text = _extract_output_text(body)
        try:
            output = OpenAIReviewOutput.model_validate_json(output_text)
        except (ValidationError, ValueError) as error:
            raise ProviderStructuredOutputError from error
        return RunExecutionResult(
            task_summary=output.task_summary,
            interpreted_intent=output.interpreted_intent,
            context=execution_context_summary(request.context_pack),
            warnings=output.warnings,
            recommended_next_steps=output.recommended_next_steps,
            proposal_draft=output.proposal_draft,
        )


def _review_output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "taskSummary": {"type": "string", "minLength": 1, "maxLength": 1000},
            "interpretedIntent": {"type": "string", "minLength": 1, "maxLength": 1000},
            "warnings": {
                "type": "array",
                "maxItems": 8,
                "items": {"type": "string", "minLength": 1, "maxLength": 300},
            },
            "recommendedNextSteps": {
                "type": "array",
                "minItems": 1,
                "maxItems": 8,
                "items": {"type": "string", "minLength": 1, "maxLength": 300},
            },
            "proposalDraft": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "summary": {"type": "string", "minLength": 1, "maxLength": 1000},
                    "rationale": {"type": "string", "minLength": 1, "maxLength": 2000},
                    "fileChanges": {
                        "type": "array",
                        "maxItems": 16,
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "properties": {
                                "path": {"type": "string", "minLength": 1, "maxLength": 4096},
                                "changeType": {
                                    "type": "string",
                                    "enum": ["create", "modify", "delete"],
                                },
                                "language": {
                                    "anyOf": [
                                        {"type": "string", "minLength": 1, "maxLength": 80},
                                        {"type": "null"},
                                    ]
                                },
                                "proposedText": {
                                    "anyOf": [
                                        {"type": "string", "maxLength": 32768},
                                        {"type": "null"},
                                    ]
                                },
                            },
                            "required": ["path", "changeType", "language", "proposedText"],
                        },
                    },
                },
                "required": ["summary", "rationale", "fileChanges"],
            },
        },
        "required": [
            "taskSummary",
            "interpretedIntent",
            "warnings",
            "recommendedNextSteps",
            "proposalDraft",
        ],
    }


def _extract_output_text(body: Any) -> str:
    if not isinstance(body, dict) or body.get("status") != "completed":
        raise ProviderUpstreamError
    output = body.get("output")
    if not isinstance(output, list):
        raise ProviderStructuredOutputError
    texts: list[str] = []
    for item in output:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        content = item.get("content")
        if not isinstance(content, list):
            continue
        for part in content:
            if isinstance(part, dict) and part.get("type") == "output_text":
                text = part.get("text")
                if isinstance(text, str):
                    texts.append(text)
    if len(texts) != 1:
        raise ProviderStructuredOutputError
    try:
        json.loads(texts[0])
    except json.JSONDecodeError as error:
        raise ProviderStructuredOutputError from error
    return texts[0]
