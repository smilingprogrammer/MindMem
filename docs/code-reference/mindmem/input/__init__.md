# `mindmem/input/__init__.py`

## Purpose

Defines the public input API by re-exporting `RawTextInput`, `TextInputEvent`,
`InputValidationError`, and `create_text_input_event`. This gives callers a stable
import path without depending on the internal module layout.
