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
        """
        Method ini TIDAK LAGI digunakan oleh orchestrator.
        Semua panggilan LLM dilakukan langsung oleh Orchestrator via _get_agent_llm().
        Dipertahankan sebagai interface agar agent bisa digunakan secara standalone jika diperlukan.
        """
        raise NotImplementedError(
            f"Agent {self.name.value}.process_message() tidak diimplementasikan. "
            f"Gunakan Orchestrator untuk menjalankan agent via LLM provider."
        )
