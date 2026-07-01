import uuid
from fastapi import APIRouter
from typing import List
from core.schemas import AgentAISetting, AgentAISettingUpdate, TeamConfig, SigmaEvent
from core.state_manager import state_manager
from core.event_bus import event_bus
from core.db import database_manager

router = APIRouter(prefix="/config", tags=["config"])

@router.get("")
async def get_config(project_id: str):
    """Mendapatkan konfigurasi tim proyek saat ini."""
    config = await state_manager.get_team_config(project_id)
    return config

@router.post("")
async def save_config(project_id: str, config: TeamConfig):
    """Menyimpan atau merubah konfigurasi tim proyek."""
    await state_manager.save_team_config(project_id, config)
    
    # Broadcast event konfigurasi berubah
    await event_bus.publish(
        project_id,
        SigmaEvent(
            event_id=str(uuid.uuid4()),
            project_id=project_id,
            event_type="config_changed",
            payload=config.model_dump()
        )
    )
    return {"status": "success", "config": config}

@router.get("/agent-ai", response_model=List[AgentAISetting])
async def get_agent_ai_settings(project_id: str):
    """Mendapatkan konfigurasi provider AI per agent tanpa membuka API key."""
    return await database_manager.get_agent_ai_settings(project_id)

@router.post("/agent-ai", response_model=AgentAISetting)
async def save_agent_ai_setting(project_id: str, setting: AgentAISettingUpdate):
    """Menyimpan konfigurasi provider AI per agent. API key disimpan terenkripsi."""
    saved = await database_manager.save_agent_ai_setting(project_id, setting)
    await event_bus.publish(
        project_id,
        SigmaEvent(
            event_id=str(uuid.uuid4()),
            project_id=project_id,
            event_type="agent_ai_config_changed",
            payload=saved.model_dump(),
        )
    )
    return saved

import httpx
from core.schemas import KeyValidationRequest

@router.post("/validate-key")
async def validate_api_key(req: KeyValidationRequest):
    """Memverifikasi validitas API Key AI secara dinamis dengan memanggil endpoint test provider."""
    provider = req.provider.strip().lower()
    key = req.api_key.strip()
    
    if not key:
        return {"valid": False, "message": "API Key kosong."}
        
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            if provider == "openai":
                headers = {"Authorization": f"Bearer {key}"}
                # Panggil list models (test standard OpenAI)
                res = await client.get("https://api.openai.com/v1/models", headers=headers)
                if res.status_code == 200:
                    return {"valid": True, "message": "Koneksi sukses! API Key OpenAI valid."}
                else:
                    return {"valid": False, "message": f"Koneksi gagal (Status {res.status_code}): Kredensial tidak valid."}
                    
            elif provider == "anthropic":
                headers = {
                    "x-api-key": key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                }
                # Panggil message endpoint dengan payload minimalis untuk verifikasi token
                payload = {
                    "model": "claude-3-haiku-20240307",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "test"}]
                }
                res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
                if res.status_code in (200, 400): 
                    # 200 = valid, 400 = bad request (bisa terjadi jika parameter model salah, tapi auth berhasil)
                    # Jika auth gagal, anthropic mengembalikan 401 Unauthorized
                    if res.status_code == 401:
                        return {"valid": False, "message": "Koneksi gagal (Status 401): API Key Anthropic tidak valid."}
                    return {"valid": True, "message": "Koneksi sukses! API Key Anthropic valid."}
                else:
                    return {"valid": False, "message": f"Koneksi gagal (Status {res.status_code}): Kredensial tidak valid."}
                    
            elif provider == "gemini":
                # Panggil endpoint list models Gemini menggunakan header X-goog-api-key
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
                gemini_headers = {
                    "Content-Type": "application/json",
                    "X-goog-api-key": key,
                }
                mini_payload = {"contents": [{"parts": [{"text": "hi"}]}], "generationConfig": {"maxOutputTokens": 1}}
                res = await client.post(url, headers=gemini_headers, json=mini_payload)
                if res.status_code == 200:
                    return {"valid": True, "message": "Koneksi sukses! API Key Gemini valid & siap digunakan."}
                else:
                    return {"valid": False, "message": f"Koneksi gagal (Status {res.status_code}): API Key Gemini tidak valid."}
            else:
                return {"valid": False, "message": f"Provider '{provider}' tidak didukung untuk validasi langsung."}
        except Exception as e:
            return {"valid": False, "message": f"Gagal menghubungi server provider: {str(e)}"}
