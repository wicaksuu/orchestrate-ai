from core.agent import BaseAgent
from core.constants import AgentName

class CoderAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.CODER, "Coder menulis kode implementasi utama sesuai instruksi.")
