import logging
from core.llm.base import LLMProvider
from core.llm.anthropic_provider import AnthropicLLMProvider
from core.llm.openai_provider import OpenAILLMProvider
from core.llm.gemini_provider import GeminiLLMProvider
from core.llm.exceptions import LLMProviderError

from config import settings

logger = logging.getLogger(__name__)


PRODUCTION_PROVIDERS = {"anthropic", "openai", "codex", "gemini"}

def get_llm_provider(
    provider_type: str | None = None,
    api_key: str | None = None,
) -> LLMProvider:
    """Mengambil LLM provider aktif berdasarkan konfigurasi settings."""
    selected_provider = (provider_type or settings.LLM_PROVIDER).lower()
    if selected_provider == "simulated":
        raise LLMProviderError("Provider 'simulated' tidak diizinkan pada runtime real.")

    if selected_provider == "anthropic":
        selected_key = api_key if api_key is not None else settings.ANTHROPIC_API_KEY
        if not selected_key:
            raise LLMProviderError("ANTHROPIC_API_KEY kosong untuk provider anthropic.")
        try:
            logger.info("Menggunakan AnthropicLLMProvider.")
            return AnthropicLLMProvider(api_key=selected_key)
        except Exception as e:
            logger.error("Gagal menginisialisasi AnthropicLLMProvider.")
            raise LLMProviderError("Gagal menginisialisasi Anthropic provider.") from e

    if selected_provider in {"openai", "codex"}:
        selected_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not selected_key:
            raise LLMProviderError(f"OPENAI_API_KEY kosong untuk provider {selected_provider}.")
        try:
            logger.info("Menggunakan OpenAILLMProvider.")
            return OpenAILLMProvider(
                api_key=selected_key,
                base_url=settings.OPENAI_BASE_URL,
            )
        except Exception as e:
            logger.error("Gagal menginisialisasi OpenAILLMProvider.")
            raise LLMProviderError("Gagal menginisialisasi OpenAI provider.") from e

    if selected_provider == "gemini":
        selected_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if not selected_key:
            raise LLMProviderError("GEMINI_API_KEY kosong untuk provider gemini.")
        try:
            logger.info("Menggunakan GeminiLLMProvider.")
            return GeminiLLMProvider(api_key=selected_key)
        except Exception as e:
            logger.error(f"Gagal menginisialisasi GeminiLLMProvider: {e}.")
            raise LLMProviderError("Gagal menginisialisasi Gemini provider.") from e

    raise LLMProviderError(
        f"Provider '{selected_provider}' tidak dikenal. Gunakan salah satu: "
        f"{', '.join(sorted(PRODUCTION_PROVIDERS))}."
    )
