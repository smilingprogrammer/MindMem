from dataclasses import dataclass
from typing import Any, Literal, Mapping, Protocol, Sequence

from jsonschema import ValidationError as JSONSchemaValidationError
from jsonschema import validate
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mindmem.input.text import TextInputEvent
from mindmem.sensory.lightweight_relevance import RelevanceResult


LLM_RELEVANT_THRESHOLD = 0.40

SYSTEM_PROMPT = """Classify whether the user message contains information useful for memory.
Relevant information includes durable facts, preferences, goals, plans, tasks,
commitments, corrections, relationships, and meaningful updates. Noise includes
filler, acknowledgements, and content with no likely future value.

Return a relevance score from 0 to 1. Use label \"relevant\" when the score is
at least 0.40; otherwise use \"noise\". Consider context only when it changes
the meaning of the message. If the schema requests a reason, use one short
sentence. Follow the supplied output schema exactly."""


class LLMRelevanceInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="The current user message to classify.")
    context: list[str] = Field(
        description="Recent messages used only to disambiguate the current message."
    )

    @field_validator("text")
    @classmethod
    def text_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("text must not be empty")
        return value


class _ResultWithoutReason(BaseModel):
    model_config = ConfigDict(extra="forbid")

    score: float = Field(
        ge=0.0,
        le=1.0,
        description="Memory relevance from 0 (none) to 1 (strong).",
    )
    label: Literal["noise", "relevant"] = Field(
        description="Relevant when score is at least 0.40; otherwise noise."
    )


class _ResultWithReason(_ResultWithoutReason):
    reason: str = Field(description="One short sentence explaining the score.")

    @field_validator("reason")
    @classmethod
    def reason_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("reason must not be empty")
        return value


LLM_RELEVANCE_INPUT_SCHEMA = LLMRelevanceInput.model_json_schema()
LLM_RELEVANCE_OUTPUT_SCHEMA = _ResultWithoutReason.model_json_schema()
LLM_RELEVANCE_OUTPUT_WITH_REASON_SCHEMA = _ResultWithReason.model_json_schema()


@dataclass(frozen=True)
class LLMRelevanceResult:
    score: float
    label: Literal["noise", "relevant"]
    reason: str | None = None


class JSONLLMProvider(Protocol):
    def generate_json(
        self,
        *,
        input_data: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]: ...


class LLMScoringNotRequired(ValueError):
    pass


class LLMResponseValidationError(ValueError):
    pass


class LLMRelevanceScorer:
    def __init__(self, provider: JSONLLMProvider):
        self.provider = provider

    def score(
        self,
        event: TextInputEvent,
        heuristic_result: RelevanceResult,
        *,
        context: Sequence[str] = (),
        include_reason: bool = False,
    ) -> LLMRelevanceResult:
        if heuristic_result.label != "unclear":
            raise LLMScoringNotRequired(
                "LLM scoring only runs when heuristic relevance is unclear"
            )

        request = LLMRelevanceInput(text=event.text, context=list(context))
        input_data = request.model_dump(mode="json")
        validate(instance=input_data, schema=LLM_RELEVANCE_INPUT_SCHEMA)

        result_model = _ResultWithReason if include_reason else _ResultWithoutReason
        output_schema = (
            LLM_RELEVANCE_OUTPUT_WITH_REASON_SCHEMA
            if include_reason
            else LLM_RELEVANCE_OUTPUT_SCHEMA
        )
        raw_result = self.provider.generate_json(
            input_data=input_data,
            output_schema=output_schema,
            instructions=SYSTEM_PROMPT,
        )

        try:
            validate(instance=raw_result, schema=output_schema)
            parsed = result_model.model_validate(raw_result)
        except (JSONSchemaValidationError, ValueError) as exc:
            raise LLMResponseValidationError("LLM output failed schema validation") from exc

        expected_label = (
            "relevant" if parsed.score >= LLM_RELEVANT_THRESHOLD else "noise"
        )
        if parsed.label != expected_label:
            raise LLMResponseValidationError(
                "LLM label does not match the relevance score"
            )

        return LLMRelevanceResult(
            score=parsed.score,
            label=parsed.label,
            reason=getattr(parsed, "reason", None),
        )
