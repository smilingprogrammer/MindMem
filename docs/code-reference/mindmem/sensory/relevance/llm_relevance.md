# `mindmem/sensory/relevance/llm_relevance.py`

## Purpose

Uses an LLM only when lightweight relevance returns `unclear`. The LLM returns a
score; Python derives `noise` or `relevant` at `0.40`.

## Classes

### `LLMRelevanceInput`

Validates current text and optional recent context. Needed for predictable LLM input.

### `_ResultWithoutReason`

Validates score-only output. Needed to minimize output tokens by default.

### `_ResultWithReason`

Validates score plus a short reason. Needed when callers explicitly request an
explanation.

### `LLMRelevanceResult`

Immutable application result containing score, Python-derived label, and optional
reason. Needed as the downstream relevance contract.

### `JSONLLMProvider`

Protocol for structured provider calls. Needed for provider independence.

### `LLMScoringNotRequired`

Raised when callers try LLM scoring on a non-unclear heuristic result. Needed to
enforce the cost-saving pipeline boundary.

### `LLMResponseValidationError`

Raised for invalid provider output. Needed to prevent malformed scores entering the
pipeline.

### `LLMRelevanceScorer`

Coordinates request schemas, provider calls, validation, and label derivation. Needed
as the LLM relevance entry point.

## Functions and methods

### `LLMRelevanceInput.text_must_not_be_empty()`

Rejects blank messages. Needed because a string schema can still contain whitespace.

### `_ResultWithReason.reason_must_not_be_empty()`

Rejects empty requested reasons. Needed to ensure paid reason output is useful.

### `JSONLLMProvider.generate_json()`

Defines the provider method required by the scorer. Needed for interchangeable APIs.

### `LLMRelevanceScorer.__init__(provider)`

Stores the provider dependency. Needed for configuration and testing.

### `LLMRelevanceScorer.score(...)`

Requires an unclear heuristic result, validates input/output JSON, calls the provider,
and derives the label. Needed to resolve cases the lightweight scorer cannot decide.
