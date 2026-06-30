from core.llm import get_llm_provider
from core.llm.openai_provider import OpenAILLMProvider
from core.llm.simulated import SimulatedLLMProvider
from config import settings


def reset_settings():
    settings.LLM_PROVIDER = "simulated"
    settings.ANTHROPIC_API_KEY = ""
    settings.OPENAI_API_KEY = ""


def test_default_provider_is_simulated():
    reset_settings()
    settings.LLM_PROVIDER = "simulated"
    provider = get_llm_provider()
    assert isinstance(provider, SimulatedLLMProvider)


def test_anthropic_without_key_falls_back_to_simulated():
    reset_settings()
    settings.LLM_PROVIDER = "anthropic"
    settings.ANTHROPIC_API_KEY = ""
    provider = get_llm_provider()
    assert isinstance(provider, SimulatedLLMProvider)


def test_openai_without_key_falls_back_to_simulated():
    reset_settings()
    settings.LLM_PROVIDER = "openai"
    settings.OPENAI_API_KEY = ""
    provider = get_llm_provider()
    assert isinstance(provider, SimulatedLLMProvider)


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
