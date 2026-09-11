# `mindmem/sensory/extraction/llm_extraction.py`

## Purpose

Extracts schema-constrained memory information from relevant text in one LLM call.

## Plain-English Context

This file turns a relevant sentence into structured memory. For example, “Apollo's
deadline is Friday” becomes entities and an atomic fact with exact source evidence.
It calls `llm_providers.py`, validates the answer, and sends the result toward
`short_term.py`.

## Classes

### `MemoryExtractionInput`

Validates the text, speaker ID, and timestamp sent to the LLM. Needed to guarantee
structured provider input.

### `EntityExtraction`

Represents an entity with type, exact evidence, and confidence. Needed to identify
the objects involved in memory.

### `FactExtraction`

Represents an atomic subject-relation-object fact. Needed for retrieval and future
knowledge-graph storage.

### `TemporalExtraction`

Connects an unnormalized time expression to a fact or event. Needed to preserve when
information applies before temporal normalization is implemented.

### `MemoryExtractionResult`

Contains source text, memory types, entities, facts, and temporal expressions. Needed
as the validated extraction contract passed into memory.

### `JSONLLMProvider`

Protocol requiring `generate_json()`. Needed so extraction works with any provider
adapter implementing the same structured interface.

### `ExtractionValidationError`

Signals invalid schema, evidence, source text, or duplicates. Needed to prevent bad
LLM output from entering memory.

### `LLMMemoryExtractor`

Coordinates input validation, provider execution, schema validation, and semantic
checks. Needed as the extraction entry point.

## Functions and methods

### `MemoryExtractionInput.value_must_not_be_empty()`

Rejects blank required fields. Needed because schema type checks alone allow blanks.

### `JSONLLMProvider.generate_json()`

Defines the provider contract. Needed for provider-independent extraction.

### `_normalized(value)`

Case-folds and normalizes whitespace. Needed for reliable duplicate detection.

### `_validate_result(result, source_text)`

Checks exact source text, evidence spans, and duplicate entities/facts. Needed because
valid JSON structure does not guarantee grounded extraction.

### `LLMMemoryExtractor.__init__(provider)`

Stores the selected provider. Needed for dependency injection and testing.

### `LLMMemoryExtractor.extract(event)`

Builds input JSON, sends the output schema, validates the response, and returns a
`MemoryExtractionResult`. Needed to safely transform text into memory-ready data.
