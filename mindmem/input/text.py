from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4


@dataclass(frozen=True)
class RawTextInput:
    user_id: str
    session_id: str
    text: str
    source: str = "chat"
    timestamp: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class TextInputEvent:
    id: str
    user_id: str
    session_id: str
    source: str
    modality: str
    timestamp: str
    text: str
    metadata: dict[str, object]


class InputValidationError(ValueError):
    pass


def create_text_input_event(raw: RawTextInput) -> TextInputEvent:
    text = raw.text.strip()

    if not raw.user_id.strip():
        raise InputValidationError("user_id is required")

    if not raw.session_id.strip():
        raise InputValidationError("session_id is required")

    if not text:
        raise InputValidationError("text is required")

    return TextInputEvent(
        id=str(uuid4()),
        user_id=raw.user_id,
        session_id=raw.session_id,
        source=raw.source,
        modality="text",
        timestamp=raw.timestamp or datetime.now(timezone.utc).isoformat(),
        text=text,
        metadata=raw.metadata,
    )
