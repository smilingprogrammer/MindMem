# `examples/llm_scoring.py`

## Purpose

Demonstrates heuristic-first relevance scoring and conditional LLM scoring.

## Functions

### `main(include_reason=False)`

Loads `.env`, creates a provider/scorer, processes predefined examples, and prints
heuristic and optional LLM results. Needed as a runnable relevance integration check.
