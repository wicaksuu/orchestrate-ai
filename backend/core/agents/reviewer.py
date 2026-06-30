from core.agent import BaseAgent
from core.constants import AgentName

class ReviewerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.REVIEWER, "Reviewer melakukan review kode yang ditulis Coder.")
