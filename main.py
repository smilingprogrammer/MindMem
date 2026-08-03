from mindmem_input import RawTextInput, create_text_input_event

raw_input = RawTextInput(
    user_id="user_1",
    session_id="session_1",
    text="I prefer short answers.",
    metadata={
        "timezone": "Africa/Lagos",
        "is_mobile": True,
    },
)

event = create_text_input_event(raw_input)

print(event)