import logging
from core.llm.base import LLMProvider
from core.llm.simulated import SimulatedLLMProvider
from core.llm.anthropic_provider import AnthropicLLMProvider

from config import settings

logger = logging.getLogger(__name__)

def get_llm_provider() -> LLMProvider:
    """Mengambil LLM provider aktif berdasarkan konfigurasi settings."""
    provider_type = settings.LLM_PROVIDER.lower()
    api_key = settings.ANTHROPIC_API_KEY

    if provider_type == "anthropic":
        if not api_key:
            logger.warning(
                "WARNING: LLM_PROVIDER diset ke 'anthropic' tetapi ANTHROPIC_API_KEY kosong! "
                "Melakukan fallback otomatis ke 'SimulatedLLMProvider' untuk development."
            )
            return SimulatedLLMProvider()
        try:
            logger.info("Menggunakan AnthropicLLMProvider.")
            return AnthropicLLMProvider(api_key=api_key)
        except Exception as e:
            logger.error("Gagal menginisialisasi AnthropicLLMProvider. Fallback ke Simulated.")
            return SimulatedLLMProvider()

    logger.info("Menggunakan SimulatedLLMProvider (Default).")
    return SimulatedLLMProvider()
