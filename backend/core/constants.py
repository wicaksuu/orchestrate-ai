from enum import Enum

class AgentName(str, Enum):
    LEAD_CONSULTANT = "LeadConsultant"
    MANAGER = "Manager"
    UI_UX_DESIGNER = "UiUxDesigner"
    PROMPT_ENGINEER = "PromptEngineer"
    CODER = "Coder"
    REVIEWER = "Reviewer"
    TESTER = "Tester"
    INTEGRATOR = "Integrator"

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    THINKING = "THINKING"
    WORKING = "WORKING"
    WAITING_REVIEW = "WAITING_REVIEW"
    WAITING_USER_INPUT = "WAITING_USER_INPUT"
    DONE = "DONE"
    BLOCKED = "BLOCKED"
    ERROR = "ERROR"

class MessageType(str, Enum):
    USER = "user"
    AGENT_COMM = "agent_comm"
    SYSTEM = "system"
    LOG = "log"
    # Protokol resmi AGENT.md
    TASK = "TASK"
    STATUS = "STATUS"
    REVIEW = "REVIEW"
    TEST_RESULT = "TEST_RESULT"
    ESCALATION = "ESCALATION"
    PHYSICAL_REQUEST = "PHYSICAL_REQUEST"
    APPROVAL_REQUEST = "APPROVAL_REQUEST"

class MessagePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
