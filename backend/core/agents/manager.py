from core.agent import BaseAgent
from core.constants import AgentName, AgentStatus

class ManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.MANAGER, "Manager bertugas mengelola alur kerja dan membagi task ke Coder.")
