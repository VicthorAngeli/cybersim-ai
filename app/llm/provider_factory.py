from app.core.config import get_settings
from app.llm.base_provider import LLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.llm.openai_compatible_provider import OpenAICompatibleProvider


def create_provider(provider: str | None = None) -> LLMProvider:
    selected = (provider or get_settings().llm_provider).casefold()
    if selected == "mock":
        return MockLLMProvider()
    if selected in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider()
    raise ValueError(f"Provedor LLM não suportado: {selected}")
