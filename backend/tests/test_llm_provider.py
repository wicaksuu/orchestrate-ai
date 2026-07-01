import pytest

from core.llm import get_llm_provider
from core.llm.anthropic_provider import AnthropicLLMProvider
from core.llm.gemini_provider import GeminiLLMProvider
from core.llm.exceptions import LLMProviderError
from core.llm.openai_provider import OpenAILLMProvider
from config import settings


def reset_settings():
    settings.LLM_PROVIDER = "gemini"
    settings.ANTHROPIC_API_KEY = ""
    settings.OPENAI_API_KEY = ""
    settings.GEMINI_API_KEY = ""


def test_unknown_provider_raises_error():
    reset_settings()
    with pytest.raises(LLMProviderError):
        get_llm_provider("simulated")


def test_anthropic_without_key_raises_error():
    reset_settings()
    settings.LLM_PROVIDER = "anthropic"
    settings.ANTHROPIC_API_KEY = ""
    with pytest.raises(LLMProviderError):
        get_llm_provider()


def test_openai_without_key_raises_error():
    reset_settings()
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = ""
    with pytest.raises(LLMProviderError):
        get_llm_provider()


def test_openai_provider_can_be_selected_with_key():
    reset_settings()
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = "test-key"
    provider = get_llm_provider()
    assert isinstance(provider, OpenAILLMProvider)
    reset_settings()


def test_codex_alias_selects_openai_provider_with_key():
    reset_settings()
    settings.LLM_PROVIDER = "codex"
    settings.OPENAI_API_KEY = "test-key"
    provider = get_llm_provider()
    assert isinstance(provider, OpenAILLMProvider)
    reset_settings()


def test_anthropic_provider_can_be_selected_with_key():
    reset_settings()
    settings.LLM_PROVIDER = "anthropic"
    settings.ANTHROPIC_API_KEY = "test-key"
    provider = get_llm_provider()
    assert isinstance(provider, AnthropicLLMProvider)
    reset_settings()


def test_gemini_provider_can_be_selected_with_key():
    reset_settings()
    settings.LLM_PROVIDER = "gemini"
    settings.GEMINI_API_KEY = "test-key"
    provider = get_llm_provider()
    assert isinstance(provider, GeminiLLMProvider)
    reset_settings()
