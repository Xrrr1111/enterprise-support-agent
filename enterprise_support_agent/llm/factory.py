"""LLM adapter factory."""

from __future__ import annotations

from enterprise_support_agent.config import Settings
from enterprise_support_agent.llm.base import LLMClient
from enterprise_support_agent.llm.http_adapters import OllamaLLM, OpenAICompatibleLLM
from enterprise_support_agent.llm.mock import MockLLM


def create_llm(settings: Settings) -> LLMClient:
    provider = settings.llm_provider.lower()
    if provider == "mock":
        return MockLLM()
    if provider == "openai":
        return OpenAICompatibleLLM(settings.llm_model, settings.api_base_url)
    if provider == "ollama":
        return OllamaLLM(settings.llm_model, settings.ollama_base_url)
    raise ValueError(f"Unsupported ESA_LLM_PROVIDER: {settings.llm_provider}")
