# `mindmem/sensory/relevance/llm_providers.py`

## Purpose

Adapts OpenAI, Anthropic, and Gemini APIs to one schema-constrained JSON interface.

## Classes

### `ProviderDependencyError`

Reports a missing optional SDK. Needed to give provider-specific installation errors.

### `ProviderResponseError`

Reports invalid provider JSON. Needed to separate transport/output failures from
memory validation failures.

### `OpenAIProvider`

Uses OpenAI chat completions with strict JSON Schema output. `__init__()` creates the
client and stores the model; `generate_json()` sends instructions/input and parses
the response. Needed for OpenAI and OpenAI-compatible endpoints.

### `AnthropicProvider`

Uses Anthropic messages with JSON Schema output. `__init__()` creates the client and
stores model/token settings; `generate_json()` calls the API and parses the text
block. Needed for Anthropic models.

### `GeminiProvider`

Uses Gemini interactions with JSON response formatting. `__init__()` creates the
client and stores the model; `generate_json()` calls the API and parses output text.
Needed for Gemini models.

## Functions

### `_parse_json(text, provider_name)`

Parses JSON and requires a top-level object. Needed to give consistent validated
provider output to relevance and extraction code.
