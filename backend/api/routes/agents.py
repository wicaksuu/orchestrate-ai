from fastapi import APIRouter
from typing import List, Optional
from core.schemas import AgentState
from core.constants import AgentName
from core.state_manager import state_manager

router = APIRouter(prefix="/agents", tags=["agents"])

@router.get("", response_model=List[AgentState])
async def get_agents(project_id: Optional[str] = None):
    """Mengembalikan status seluruh agent di platform."""
    states = []
    for agent_name in AgentName:
        state = await state_manager.get_agent_state(agent_name.value, project_id)
        states.append(state)
    return states
