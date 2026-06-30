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
