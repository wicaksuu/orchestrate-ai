import logging
from typing import Dict, List

import httpx

from core.llm.base import LLMProvider
from core.llm.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


class OpenAILLMProvider(LLMProvider):
    """OpenAI provider using the Responses API."""

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
    ):
        if not api_key:
            raise ValueError("OPENAI_API_KEY must be set when using OpenAI provider.")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    async def complete(
        self,
        *,
        system_prompt: str,
        messages: List[Dict[str, str]],
        model: str,
        max_tokens: int = 4000,
    ) -> str:
        payload = {
            "model": model,
            "instructions": system_prompt,
            "input": [
                {
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                }
                for msg in messages
            ],
            "max_output_tokens": max_tokens,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/responses",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                output_text = data.get("output_text")
                if isinstance(output_text, str) and output_text:
                    return output_text

                output = data.get("output", [])
                text_parts: list[str] = []
                for item in output:
                    for content in item.get("content", []):
                        text = content.get("text")
                        if isinstance(text, str):
                            text_parts.append(text)
                if text_parts:
                    return "\n".join(text_parts)

                raise LLMProviderError("OpenAI response did not contain text output.")
            except LLMProviderError:
                raise
            except Exception:
                logger.error("OpenAI Responses API call failed.")
                raise LLMProviderError(
                    "Terjadi error internal pada OpenAI provider saat memproses permintaan."
                )
