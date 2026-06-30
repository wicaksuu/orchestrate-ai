import logging
from typing import Dict, List
import httpx

from core.llm.base import LLMProvider
from core.llm.exceptions import LLMProviderError

logger = logging.getLogger(__name__)

class GeminiLLMProvider(LLMProvider):
  """Google Gemini API Provider menggunakan HTTP REST API untuk reliabilitas tinggi tanpa dependensi tambahan."""

  def __init__(self, *, api_key: str):
    if not api_key:
      raise ValueError("GEMINI_API_KEY harus diisi untuk menggunakan Gemini provider.")
    self.api_key = api_key
    self.base_url = "https://generativelanguage.googleapis.com/v1beta"

  async def complete(
    self,
    *,
    system_prompt: str,
    messages: List[Dict[str, str]],
    model: str,
    max_tokens: int = 4000,
  ) -> str:
    # Model default gratis adalah gemini-1.5-flash jika model tidak dispesifikasikan dengan valid
    gemini_model = model if model.startswith("gemini-") else "gemini-1.5-flash"
    
    # Konversi pesan ke format Gemini API (role 'assistant' diubah menjadi 'model')
    gemini_contents = []
    for msg in messages:
      role = msg.get("role", "user")
      if role == "assistant":
        role = "model"
      gemini_contents.append({
        "role": role,
        "parts": [{"text": msg.get("content", "")}]
      })

    payload = {
      "contents": gemini_contents,
      "generationConfig": {
        "maxOutputTokens": max_tokens,
      }
    }

    if system_prompt:
      payload["systemInstruction"] = {
        "parts": [{"text": system_prompt}]
      }

    url = f"{self.base_url}/models/{gemini_model}:generateContent?key={self.api_key}"
    headers = {"Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=60.0) as client:
      try:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code != 200:
          logger.error(f"Gemini API Error: Status {response.status_code} - {response.text}")
          raise LLMProviderError(f"Gemini API mengembalikan status {response.status_code}: {response.text}")
          
        data = response.json()
        candidates = data.get("candidates", [])
        if not candidates:
          # Cek jika terkena filter keamanan Google
          prompt_feedback = data.get("promptFeedback", {})
          if prompt_feedback:
            raise LLMProviderError(f"Permintaan ditolak oleh filter keamanan Gemini: {prompt_feedback}")
          raise LLMProviderError("Gemini API tidak mengembalikan respons teks (candidates kosong).")

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])
        if not parts:
          raise LLMProviderError("Struktur respons Gemini tidak valid (parts kosong).")

        return parts[0].get("text", "")
      except httpx.HTTPError as e:
        logger.error(f"HTTP error terjadi saat memanggil Gemini API: {e}")
        raise LLMProviderError(f"Gagal menghubungi server Gemini: {str(e)}")
      except Exception as e:
        if isinstance(e, LLMProviderError):
          raise e
        logger.error(f"Error tidak terduga pada Gemini provider: {e}")
        raise LLMProviderError(f"Terjadi error internal pada Gemini provider: {str(e)}")
