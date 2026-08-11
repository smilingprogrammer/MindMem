# `examples/short_term_memory.py`

## Purpose

Runs the complete implemented pipeline interactively: input, relevance, extraction,
short-term storage, topic grouping, and working state.

## Functions

### `main()`

Loads provider configuration, creates all pipeline components, reads user messages,
and handles `/memories`, `/topics`, `/state`, `/context`, `/decision`, `/task`,
`/tool`, `/complete`, and `/exit`. Needed as an end-to-end manual test and usage
example.
