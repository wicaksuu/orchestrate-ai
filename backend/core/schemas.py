from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.constants import AgentName, AgentStatus, MessageType, MessagePriority

class MessageMetadata(BaseModel):
    """Metadata untuk pesan agent."""
    sender: str
    receiver: str
    step_id: Optional[str] = None
    token_estimate: Optional[int] = 0
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentMessage(BaseModel):
    """Representasi pesan yang dikirim oleh agent atau user."""
    id: str
    project_id: str
    message_type: MessageType
    content: str
    priority: MessagePriority = MessagePriority.MEDIUM
    metadata: MessageMetadata
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SigmaEvent(BaseModel):
    """Representasi event pub/sub untuk dikirim ke UI melalui WebSocket."""
    event_id: str
    project_id: str
    event_type: str  # e.g., "agent_status", "message", "escalation", "config_changed"
    payload: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class AgentState(BaseModel):
    """Status representasi internal untuk tiap agent."""
    name: AgentName
    status: AgentStatus
    last_message: Optional[str] = None
    token_count: int = 0
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class TeamConfig(BaseModel):
    """Konfigurasi tim agent."""
    coder_count: int = Field(default=1, ge=1, le=5)
    active_roles: Dict[str, bool] = Field(default_factory=lambda: {
        "Documenter": False,
        "Integrator": True,
        "Reviewer": True,
        "Tester": True,
        "PromptEngineer": True,
    })
    models: Dict[str, str] = Field(default_factory=lambda: {
        "LeadConsultant": "claude-sonnet-4-6",
        "Manager": "claude-sonnet-4-6",
        "PromptEngineer": "claude-haiku-4-5-20251001",
        "Coder": "claude-sonnet-4-6",
        "Reviewer": "claude-sonnet-4-6",
        "Tester": "claude-sonnet-4-6",
        "Integrator": "claude-sonnet-4-6",
    })

class ProjectState(BaseModel):
    """Status proyek saat ini."""
    project_id: str
    name: str
    description: Optional[str] = None
    status: str = "init"  # init, discovery, planning, development, testing, completed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class EscalationRequest(BaseModel):
    """Eskalasi yang membutuhkan input/approval user."""
    id: str
    project_id: str
    agent_name: AgentName
    description: str  # Deskripsi dalam Bahasa Indonesia
    options: Optional[List[str]] = None  # Tombol pilihan jika ada
    timeout_seconds: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    resolved: bool = False
    response: Optional[str] = None

class SandboxCommand(BaseModel):
    """Command yang akan dijalankan di Sandbox."""
    command: str
    args: List[str] = []
    timeout: int = 120

class SandboxResult(BaseModel):
    """Hasil eksekusi command di Sandbox."""
    stdout: str
    stderr: str
    return_code: int
    duration_ms: float
