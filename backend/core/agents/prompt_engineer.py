from core.agent import BaseAgent
from core.constants import AgentName

class PromptEngineerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.PROMPT_ENGINEER, "Prompt Engineer mengoptimalkan prompt LLM untuk agent lainnya.")
