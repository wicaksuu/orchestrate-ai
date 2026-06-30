import logging
from core.llm.base import LLMProvider
from core.llm.simulated import SimulatedLLMProvider
from core.llm.anthropic_provider import AnthropicLLMProvider
from core.llm.openai_provider import OpenAILLMProvider
from core.llm.gemini_provider import GeminiLLMProvider

from config import settings

logger = logging.getLogger(__name__)

def get_llm_provider(
    provider_type: str | None = None,
    api_key: str | None = None,
) -> LLMProvider:
    """Mengambil LLM provider aktif berdasarkan konfigurasi settings."""
    selected_provider = (provider_type or settings.LLM_PROVIDER).lower()

    if selected_provider == "anthropic":
        selected_key = api_key if api_key is not None else settings.ANTHROPIC_API_KEY
        if not selected_key:
            logger.warning(
                "WARNING: LLM_PROVIDER diset ke 'anthropic' tetapi ANTHROPIC_API_KEY kosong! "
                "Melakukan fallback otomatis ke 'SimulatedLLMProvider' untuk development."
            )
            return SimulatedLLMProvider()
        try:
            logger.info("Menggunakan AnthropicLLMProvider.")
            return AnthropicLLMProvider(api_key=selected_key)
        except Exception as e:
            logger.error("Gagal menginisialisasi AnthropicLLMProvider. Fallback ke Simulated.")
            return SimulatedLLMProvider()

    if selected_provider in {"openai", "codex"}:
        selected_key = api_key if api_key is not None else settings.OPENAI_API_KEY
        if not selected_key:
            logger.warning(
                "WARNING: LLM_PROVIDER diset ke '%s' tetapi OPENAI_API_KEY kosong. "
                "Melakukan fallback otomatis ke SimulatedLLMProvider.",
                selected_provider,
            )
            return SimulatedLLMProvider()
        try:
            logger.info("Menggunakan OpenAILLMProvider.")
            return OpenAILLMProvider(
                api_key=selected_key,
                base_url=settings.OPENAI_BASE_URL,
            )
        except Exception:
            logger.error("Gagal menginisialisasi OpenAILLMProvider. Fallback ke Simulated.")
            return SimulatedLLMProvider()

    if selected_provider == "gemini":
        selected_key = api_key if api_key is not None else settings.GEMINI_API_KEY
        if not selected_key:
            logger.warning(
                "WARNING: LLM_PROVIDER diset ke 'gemini' tetapi GEMINI_API_KEY kosong. "
                "Melakukan fallback otomatis ke SimulatedLLMProvider."
            )
            return SimulatedLLMProvider()
        try:
            logger.info("Menggunakan GeminiLLMProvider.")
            return GeminiLLMProvider(api_key=selected_key)
        except Exception as e:
            logger.error(f"Gagal menginisialisasi GeminiLLMProvider: {e}. Fallback ke Simulated.")
            return SimulatedLLMProvider()

    logger.info("Menggunakan SimulatedLLMProvider (Default).")
    return SimulatedLLMProvider()
