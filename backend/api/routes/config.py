import uuid
from fastapi import APIRouter
from core.schemas import TeamConfig, SigmaEvent
from core.state_manager import state_manager
from core.event_bus import event_bus

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
