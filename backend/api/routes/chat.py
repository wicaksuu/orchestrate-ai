import uuid
import logging
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from core.schemas import AgentMessage, EscalationRequest, SigmaEvent
from core.constants import AgentName, AgentStatus
from core.orchestrator import orchestrator
from core.state_manager import state_manager
from core.event_bus import event_bus

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])

class UserMessageRequest(BaseModel):
    project_id: str
    content: str

class ResolveEscalationRequest(BaseModel):
    project_id: str
    escalation_id: str
    response: str

@router.post("")
async def send_chat_message(req: UserMessageRequest, background_tasks: BackgroundTasks):
    """Mengirim pesan dari user ke Lead Consultant."""
    # Proses pesan secara background agar response cepat kembali
    background_tasks.add_task(
        orchestrator.handle_user_message, req.project_id, req.content
    )
    return {"status": "processing"}

@router.post("/escalation/resolve")
async def resolve_escalation(req: ResolveEscalationRequest):
    """Menyelesaikan eskalasi yang tertunda."""
    resolved = await state_manager.resolve_escalation(
        req.project_id, req.escalation_id, req.response
    )
    if not resolved:
        raise HTTPException(status_code=404, detail="Eskalasi tidak ditemukan.")
    
    # Broadcast event bahwa eskalasi telah diselesaikan
    await event_bus.publish(
        req.project_id,
        SigmaEvent(
            event_id=str(uuid.uuid4()),
            project_id=req.project_id,
            event_type="escalation_resolved",
            payload={"escalation_id": req.escalation_id, "response": req.response}
        )
    )
    
    # Dapatkan status LeadConsultant dan kembalikan ke IDLE
    lc_agent = orchestrator.agents[AgentName.LEAD_CONSULTANT]
    await lc_agent.update_status(AgentStatus.IDLE, f"Eskalasi diselesaikan: {req.response}")
    await event_bus.publish(
        req.project_id,
        SigmaEvent(
            event_id=str(uuid.uuid4()),
            project_id=req.project_id,
            event_type="agent_status",
            payload=(await lc_agent.get_state()).model_dump()
        )
    )

    return {"status": "resolved", "data": resolved}
