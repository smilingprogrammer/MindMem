import os

from mindmem.sensory.relevance.llm_providers import (
    AnthropicProvider,
    GeminiProvider,
    OpenAIProvider,
)


PROVIDERS = {
    "openai": (OpenAIProvider, "OPENAI_API_KEY"),
    "anthropic": (AnthropicProvider, "ANTHROPIC_API_KEY"),
    "gemini": (GeminiProvider, "GEMINI_API_KEY"),
}


def required_environment(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def create_provider():
    provider_name = required_environment("MINDMEM_LLM_PROVIDER").lower()
    model = required_environment("MINDMEM_LLM_MODEL")

    if provider_name not in PROVIDERS:
        supported = ", ".join(PROVIDERS)
        raise SystemExit(f"Unsupported provider. Choose one of: {supported}")

    provider_class, api_key_name = PROVIDERS[provider_name]
    options = {
        "model": model,
        "api_key": required_environment(api_key_name),
    }
    if provider_name == "openai" and os.getenv("OPENAI_BASE_URL"):
        options["base_url"] = os.environ["OPENAI_BASE_URL"]

    return provider_class(**options)
