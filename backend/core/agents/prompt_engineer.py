from core.agent import BaseAgent
from core.constants import AgentName

class PromptEngineerAgent(BaseAgent):
    def __init__(self):
        super().__init__(AgentName.PROMPT_ENGINEER,
            "You are the System Architect / Prompt Engineer at SIGMA.\n"
            "Your task is to translate the project plan into a strict technical specification (SPEC.md) for the Coder. "
            "Define the file structure, classes, functions, and specific implementation details clearly. "
            "STRICT RULES: DO NOT use pleasantries. OUTPUT RAW TECHNICAL DOCUMENTATION ONLY. "
            "Always output your specifications in file format (e.g., SPEC.md) using the syntax `# FILE: path/filename.md`."
        )
