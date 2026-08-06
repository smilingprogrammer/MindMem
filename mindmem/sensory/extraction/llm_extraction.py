from typing import Any, Literal, Mapping, Protocol

from jsonschema import ValidationError as JSONSchemaValidationError
from jsonschema import validate
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mindmem.input.text import TextInputEvent


MemoryType = Literal[
    "identity",
    "preference",
    "goal",
    "task",
    "correction",
    "relationship",
    "project",
    "event",
    "other",
]

EntityType = Literal[
    "person",
    "organization",
    "place",
    "product",
    "project",
    "concept",
    "other",
]

SYSTEM_PROMPT = """Extract explicit memory information from the current user message.
Do not infer facts that are not directly stated. Use "user" for first-person
references. Write relation names in concise snake_case. Every evidence value must
be an exact, case-sensitive substring of the current message. Entity evidence is
the entity mention. Fact evidence is the shortest complete clause that states the
whole fact, not only the subject or object. Confidence measures how clearly the
message states the item, not whether the item is true. Keep temporal expressions
in their original form; do not normalize them. Copy the current message exactly
into source_text. Follow the output schema exactly."""


class MemoryExtractionInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    text: str = Field(description="The current user message.")
    speaker_id: str = Field(description="The backend identifier of the speaker.")
    timestamp: str = Field(description="When the current message was received.")

    @field_validator("text", "speaker_id", "timestamp")
    @classmethod
    def value_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value


class EntityExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(description="Entity name exactly as expressed in the message.")
    type: EntityType
    evidence: str = Field(description="Exact text span supporting this entity.")
    confidence: float = Field(ge=0.0, le=1.0)


class FactExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subject: str
    relation: str = Field(description="Concise snake_case relationship or predicate.")
    object: str
    evidence: str = Field(description="Exact text span supporting this fact.")
    confidence: float = Field(ge=0.0, le=1.0)


class TemporalExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    text: str = Field(description="Original, unnormalized temporal expression.")
    applies_to: str = Field(description="The fact or event qualified by this time.")


class MemoryExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    source_text: str
    memory_types: list[MemoryType] = Field(
        min_length=1,
        description="Categories represented by the explicit facts in the message.",
    )
    entities: list[EntityExtraction]
    facts: list[FactExtraction] = Field(min_length=1)
    temporal_expressions: list[TemporalExtraction]


MEMORY_EXTRACTION_INPUT_SCHEMA = MemoryExtractionInput.model_json_schema()
MEMORY_EXTRACTION_OUTPUT_SCHEMA = MemoryExtractionResult.model_json_schema()


class JSONLLMProvider(Protocol):
    def generate_json(
        self,
        *,
        input_data: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]: ...


class ExtractionValidationError(ValueError):
    pass


def _normalized(value: str) -> str:
    return " ".join(value.casefold().split())


def _validate_result(result: MemoryExtractionResult, source_text: str) -> None:
    if result.source_text != source_text:
        raise ExtractionValidationError("source_text does not match the input message")

    evidence_spans = [entity.evidence for entity in result.entities]
    evidence_spans.extend(fact.evidence for fact in result.facts)
    evidence_spans.extend(item.text for item in result.temporal_expressions)
    if any(evidence not in source_text for evidence in evidence_spans):
        raise ExtractionValidationError("extracted evidence is not in the input message")

    entity_keys = [(_normalized(item.name), item.type) for item in result.entities]
    if len(entity_keys) != len(set(entity_keys)):
        raise ExtractionValidationError("duplicate entities were extracted")

    fact_keys = [
        (
            _normalized(item.subject),
            _normalized(item.relation),
            _normalized(item.object),
        )
        for item in result.facts
    ]
    if len(fact_keys) != len(set(fact_keys)):
        raise ExtractionValidationError("duplicate facts were extracted")


class LLMMemoryExtractor:
    def __init__(self, provider: JSONLLMProvider):
        self.provider = provider

    def extract(self, event: TextInputEvent) -> MemoryExtractionResult:
        request = MemoryExtractionInput(
            text=event.text,
            speaker_id=event.user_id,
            timestamp=event.timestamp,
        )
        input_data = request.model_dump(mode="json")
        validate(instance=input_data, schema=MEMORY_EXTRACTION_INPUT_SCHEMA)

        raw_result = self.provider.generate_json(
            input_data=input_data,
            output_schema=MEMORY_EXTRACTION_OUTPUT_SCHEMA,
            instructions=SYSTEM_PROMPT,
        )

        try:
            validate(instance=raw_result, schema=MEMORY_EXTRACTION_OUTPUT_SCHEMA)
            result = MemoryExtractionResult.model_validate(raw_result)
        except (JSONSchemaValidationError, ValueError) as exc:
            raise ExtractionValidationError(
                "LLM extraction failed schema validation"
            ) from exc

        _validate_result(result, event.text)
        return result
