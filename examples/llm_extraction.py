from dotenv import load_dotenv

from examples.provider_setup import create_provider
from mindmem.input.text import RawTextInput, create_text_input_event
from mindmem.sensory.extraction import LLMMemoryExtractor


def main() -> None:
    load_dotenv()
    provider = create_provider()
    extractor = LLMMemoryExtractor(provider)

    event = create_text_input_event(
        RawTextInput(
            user_id="user_1",
            session_id="session_1",
            text=(
                "My name is Abdulsobur, I work at Acme, and I started there "
                "last year."
            ),
        )
    )

    result = extractor.extract(event)
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
