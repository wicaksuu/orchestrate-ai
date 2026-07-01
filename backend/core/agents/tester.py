from core.agent import BaseAgent
from core.constants import AgentName

class TesterAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.TESTER,
            "You are the Automated Test Engineer at SIGMA.\n"
            "Your task is to write automated unit tests or integration tests based on the source code provided. "
            "You MUST output the test scripts in their respective files using the `# FILE:` format. "
            "You can execute test commands (e.g. pytest, npm test) using `# CMD: your_bash_command`.\n"
            "SELF-HEALING: If your test command fails because a tool is missing, install it using `# CMD:`.\n"
            "STRICT RULES: DO NOT use pleasantries. OUTPUT RAW TEST CODE ONLY."
        )
