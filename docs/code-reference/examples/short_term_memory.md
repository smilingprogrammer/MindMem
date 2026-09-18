# `examples/short_term_memory.py`

Automatic consolidation is enabled when constructing the consolidator. Inactive
topics and topics about to lose records are saved automatically. `/exit` calls
`buffer.end_session()` to save all remaining topics. The example's long-term store
is still in RAM, so exiting the process does not persist it to disk.

## Purpose

Runs the complete implemented pipeline interactively: input, relevance, extraction,
short-term storage, topic grouping, and working state.

## Plain-English Context

This is the easiest file to run when checking how everything connects. It performs
the input-to-memory flow and provides commands to inspect what was stored. It is a
demonstration interface; reusable behavior lives under `mindmem/`.

## Functions

### `main()`

Loads provider configuration, creates all pipeline components, reads user messages,
and handles `/memories`, `/topics`, `/state`, `/context`, `/decision`, `/task`,
`/tool`, `/complete`, `/consolidate`, `/long-term`, and `/exit`. Needed as an
end-to-end manual test and usage example.
