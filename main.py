from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.sensory.lightweight_relevance import score_relevance


examples = [
    "My name is Abdulsobur and I work as a developer.",
    "Remind me tomorrow to finish the project.",
    "Okay",
]

for text in examples:
    event = create_text_input_event(
        RawTextInput(
            user_id="user_1",
            session_id="session_1",
            text=text,
        )
    )
    result = score_relevance(event)

    print(f"Input: {text}")
    print(f"Score: {result.score}")
    print(f"Label: {result.label}")
    print(f"Signals: {', '.join(result.signals)}")
    print()
