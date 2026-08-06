import json
from typing import Any, Mapping


class ProviderDependencyError(ImportError):
    pass


class ProviderResponseError(RuntimeError):
    pass


def _parse_json(text: str, provider_name: str) -> Mapping[str, Any]:
    try:
        result = json.loads(text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ProviderResponseError(
            f"{provider_name} returned an invalid JSON response"
        ) from exc

    if not isinstance(result, dict):
        raise ProviderResponseError(
            f"{provider_name} returned JSON that is not an object"
        )
    return result


class OpenAIProvider:
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderDependencyError(
                "Install the OpenAI adapter with: pip install openai"
            ) from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def generate_json(
        self,
        *,
        input_data: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": instructions},
                {
                    "role": "user",
                    "content": json.dumps(input_data, separators=(",", ":")),
                },
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_output",
                    "schema": dict(output_schema),
                    "strict": True,
                },
            },
        )
        return _parse_json(response.choices[0].message.content, "OpenAI")


class AnthropicProvider:
    def __init__(
        self,
        *,
        model: str,
        api_key: str | None = None,
        max_tokens: int = 256,
    ):
        try:
            from anthropic import Anthropic
        except ImportError as exc:
            raise ProviderDependencyError(
                "Install the Anthropic adapter with: pip install anthropic"
            ) from exc

        self.client = Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def generate_json(
        self,
        *,
        input_data: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        response = self.client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=instructions,
            messages=[
                {
                    "role": "user",
                    "content": json.dumps(input_data, separators=(",", ":")),
                }
            ],
            output_config={
                "format": {
                    "type": "json_schema",
                    "schema": dict(output_schema),
                }
            },
        )
        text = next(
            (block.text for block in response.content if block.type == "text"),
            "",
        )
        return _parse_json(text, "Anthropic")


class GeminiProvider:
    def __init__(self, *, model: str, api_key: str | None = None):
        try:
            from google import genai
        except ImportError as exc:
            raise ProviderDependencyError(
                "Install the Gemini adapter with: pip install google-genai"
            ) from exc

        self.client = genai.Client(api_key=api_key)
        self.model = model

    def generate_json(
        self,
        *,
        input_data: Mapping[str, Any],
        output_schema: Mapping[str, Any],
        instructions: str,
    ) -> Mapping[str, Any]:
        prompt = (
            f"{instructions}\n\n"
            f"Input JSON:\n{json.dumps(input_data, separators=(',', ':'))}"
        )
        interaction = self.client.interactions.create(
            model=self.model,
            input=prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": dict(output_schema),
            },
        )
        return _parse_json(interaction.output_text, "Gemini")
