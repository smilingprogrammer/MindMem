# `mindmem/input/text.py`

## Purpose

Defines and validates text entering MindMem.

## Plain-English Context

This is where every user message first becomes MindMem data. A developer supplies
raw text and backend IDs; `create_text_input_event()` rejects missing values and adds
an event ID, timestamp, and `text` modality. The resulting event is passed to
`lightweight_relevance.py`.

## Classes

### `RawTextInput`

Transport object supplied by the integrating backend. It carries user/session IDs,
text, source, an optional timestamp, and arbitrary metadata. It is needed to keep
backend input separate from MindMem's normalized event.

### `TextInputEvent`

Immutable normalized event with a generated ID, explicit `text` modality, timestamp,
and original metadata. It is needed as the common contract for sensory processing.

### `InputValidationError`

Raised for missing IDs or empty text. A dedicated error lets integrations distinguish
bad input from later sensory or provider failures.

## Functions

### `create_text_input_event(raw)`

Trims text, validates required fields, creates an event ID and UTC timestamp, and
returns `TextInputEvent`. It is needed so every downstream component receives valid,
consistent event data.
