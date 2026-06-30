import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.constants import AgentName, AgentStatus
from core.schemas import AgentState
from core.state_manager import state_manager

logger = logging.getLogger(__name__)

class BaseAgent:
    """Kelas dasar untuk seluruh agent di platform SIGMA."""
    def __init__(self, name: AgentName, system_prompt: str = ""):
        self.name = name
        self.system_prompt = system_prompt
        self.history: List[Dict[str, str]] = []
        self.token_count = 0

    async def get_state(self, project_id: Optional[str] = None) -> AgentState:
        """Mengambil state agent saat ini dari state manager."""
        return await state_manager.get_agent_state(self.name.value, project_id)

    async def update_status(self, status: AgentStatus, last_message: Optional[str] = None, project_id: Optional[str] = None):
        """Memperbarui status agent dan menyimpannya."""
        state = await self.get_state(project_id)
        state.status = status
        if last_message:
            state.last_message = last_message[:100]  # batasi panjang preview
        state.token_count = self.token_count
        await state_manager.save_agent_state(state, project_id)
        logger.info(f"Agent {self.name.value} berubah status menjadi {status.value} untuk project {project_id}")

    async def process_message(self, project_id: str, sender: str, content: str) -> str:
        """Memproses pesan masuk. Di kelas turunan, fungsi ini akan disimulasikan atau memanggil LLM."""
        self.history.append({"role": "user", "content": f"{sender}: {content}"})
        await self.update_status(AgentStatus.THINKING, project_id=project_id)
        
        # Simulasi pengerjaan / thinking time
        import asyncio
        await asyncio.sleep(1)
        
        await self.update_status(AgentStatus.WORKING, project_id=project_id)
        await asyncio.sleep(1.5)
        
        response = f"Respon simulasi dari {self.name.value} untuk {sender}."
        self.history.append({"role": "assistant", "content": response})
        self.token_count += len(content.split()) + len(response.split())  # estimasi token sederhana
        
        await self.update_status(AgentStatus.IDLE, response, project_id=project_id)
        return response
