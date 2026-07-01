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
    # Default ke gemini-flash-latest jika model tidak dispesifikasikan
    gemini_model = model if model.startswith("gemini-") else "gemini-flash-latest"
    
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

    # Daftar model gratis untuk load balancing/fallback (berdasarkan dokumen kuota AI Studio pengguna)
    FREE_FALLBACK_MODELS = [
        "gemini-3.5-flash",
        "gemini-3.1-flash-lite",
        "gemini-3-flash",
        "gemini-3.1-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
        "gemini-2-flash",
        "gemini-2-flash-lite"
    ]
    
    # Model utama ditaruh di awal, diikuti dengan model fallback
    models_to_try = [gemini_model]
    for fm in FREE_FALLBACK_MODELS:
        if fm != gemini_model:
            models_to_try.append(fm)

    headers = {
      "Content-Type": "application/json",
      "X-goog-api-key": self.api_key,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
      for idx, current_model in enumerate(models_to_try):
        url = f"{self.base_url}/models/{current_model}:generateContent"
        
        try:
          response = await client.post(url, headers=headers, json=payload)
          
          if response.status_code in [429, 500, 503]:
            # Jika ini adalah model terakhir, jangan continue, biarkan jatuh ke exception
            if idx == len(models_to_try) - 1:
              logger.error(f"Semua model fallback habis. Model {current_model} gagal: {response.text}")
              raise LLMProviderError(f"Semua model Gemini melampaui limit. Terakhir: {current_model} - {response.text}")
            
            logger.warning(f"Model {current_model} terkena {response.status_code}. Melakukan fallback ke model selanjutnya...")
            continue
            
          if response.status_code != 200:
            logger.error(f"Gemini API Error: Status {response.status_code} - {response.text}")
            raise LLMProviderError(f"Gemini API mengembalikan status {response.status_code}: {response.text}")
            
          data = response.json()
          candidates = data.get("candidates", [])
          if not candidates:
            prompt_feedback = data.get("promptFeedback", {})
            if prompt_feedback:
              raise LLMProviderError(f"Permintaan ditolak oleh filter keamanan Gemini: {prompt_feedback}")
            raise LLMProviderError(f"Gemini API ({current_model}) tidak mengembalikan respons teks (candidates kosong).")

          content = candidates[0].get("content", {})
          parts = content.get("parts", [])
          if not parts:
            raise LLMProviderError(f"Struktur respons Gemini ({current_model}) tidak valid (parts kosong).")

          return parts[0].get("text", "")
          
        except httpx.HTTPError as e:
          logger.error(f"HTTP error terjadi saat memanggil Gemini API ({current_model}): {e}")
          if idx == len(models_to_try) - 1:
            raise LLMProviderError(f"Gagal menghubungi server Gemini pada semua percobaan: {str(e)}")
          continue
        except Exception as e:
          if isinstance(e, LLMProviderError):
            raise e
          logger.error(f"Error tidak terduga pada Gemini provider: {e}")
          raise LLMProviderError(f"Terjadi error internal pada Gemini provider: {str(e)}")
