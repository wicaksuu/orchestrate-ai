from fastapi import APIRouter, Query
from typing import List
from core.schemas import SigmaEvent
from core.event_bus import event_bus

router = APIRouter(prefix="/events", tags=["events"])

@router.get("", response_model=List[SigmaEvent])
async def get_events(
    project_id: str,
    limit: int = Query(default=100, ge=1, le=1000)
):
    """Mengambil riwayat event untuk proyek."""
    return await event_bus.get_events(project_id, limit)
