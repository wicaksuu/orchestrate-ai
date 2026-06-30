from core.agent import BaseAgent
from core.constants import AgentName

class IntegratorAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.INTEGRATOR, "Integrator menggabungkan semua perubahan kode ke repositori utama.")
