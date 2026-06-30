import os
import logging
import httpx
from typing import List, Dict
from core.llm.base import LLMProvider

from core.llm.exceptions import LLMProviderError

logger = logging.getLogger(__name__)

class AnthropicLLMProvider(LLMProvider):
    """AnthropicLLMProvider memanggil API Anthropic Claude secara asinkron menggunakan httpx."""
    def __init__(self, api_key: str):
        self.api_key = api_key
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY tidak boleh kosong saat menggunakan provider anthropic.")
        
    async def complete(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4000,
    ) -> str:
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        
        # Pindahkan format messages ke standard API Anthropic jika perlu
        formatted_messages = []
        for msg in messages:
            # Map 'user' atau 'assistant'
            role = msg.get("role", "user")
            content = msg.get("content", "")
            # Bersihkan prefix user name jika ada (e.g. "User: Halo")
            if ":" in content and role == "user":
                content = content.split(":", 1)[1].strip()
            formatted_messages.append({
                "role": role,
                "content": content
            })

        data = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_prompt,
            "messages": formatted_messages
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers=headers,
                    json=data
                )
                response.raise_for_status()
                res_data = response.json()
                return res_data["content"][0]["text"]
            except Exception as e:
                logger.error("Gagal memanggil Anthropic API karena terjadi kendala runtime.")
                raise LLMProviderError("Terjadi error internal pada LLM provider saat memproses permintaan.")
