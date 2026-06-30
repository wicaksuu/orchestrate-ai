from typing import Protocol, List, Dict

class LLMProvider(Protocol):
    """Protokol abstraksi untuk LLM provider."""
    async def complete(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4000,
    ) -> str:
        """Mengirimkan prompt dan pesan ke LLM dan mengembalikan respons teks."""
        ...
