from fastapi import APIRouter
from typing import List
from core.schemas import AgentMessage, EscalationRequest
from core.state_manager import state_manager

router = APIRouter(prefix="/logs", tags=["logs"])

@router.get("", response_model=List[AgentMessage])
async def get_logs(project_id: str):
    """Mengambil riwayat log komunikasi agent untuk proyek."""
    return await state_manager.get_messages(project_id)

@router.get("/escalation", response_model=List[EscalationRequest])
async def get_escalations(project_id: str):
    """Mengambil daftar eskalasi pending untuk proyek."""
    return await state_manager.get_pending_escalations(project_id)
