# `examples/provider_setup.py`

## Purpose

Creates the configured LLM provider from environment variables for all LLM examples.

## Functions

### `required_environment(name)`

Returns a required environment value or exits with a clear error. Needed to fail early
when provider configuration is incomplete.

### `create_provider()`

Reads provider/model/API key settings, validates the provider name, optionally applies
`OPENAI_BASE_URL`, and constructs the adapter. Needed to avoid duplicating setup in
every example.
