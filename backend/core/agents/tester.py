from core.agent import BaseAgent
from core.constants import AgentName

class TesterAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.TESTER, "Tester menulis dan menjalankan unit test di Sandbox.")
