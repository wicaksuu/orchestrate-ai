from pydantic import BaseModel, Field, field_validator
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

class AgentAISetting(BaseModel):
    """Public AI provider setting for one agent. API key is never returned."""
    agent_name: str
    provider: str = "gemini"
    model: str = "gemini-flash-latest"
    api_key_configured: bool = False
    updated_at: Optional[datetime] = None

class AgentAISettingUpdate(BaseModel):
    """Update payload for one agent AI provider setting."""
    agent_name: str
    provider: str
    model: str
    api_key: Optional[str] = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().lower()
        allowed = {"openai", "codex", "anthropic", "gemini"}
        if normalized not in allowed:
            raise ValueError(f"provider harus salah satu dari: {', '.join(sorted(allowed))}")
        return normalized

    @field_validator("agent_name", "model")
    @classmethod
    def trim_required_strings(cls, value: str) -> str:
        trimmed = value.strip()
        if not trimmed:
            raise ValueError("field tidak boleh kosong")
        return trimmed

    @field_validator("api_key")
    @classmethod
    def normalize_api_key(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        trimmed = value.strip()
        return trimmed or None

class KeyValidationRequest(BaseModel):
    """Payload request untuk memvalidasi kredensial API Key AI."""
    provider: str
    api_key: str

class ProjectState(BaseModel):
    """Status proyek saat ini."""
    project_id: str
    name: str
    description: Optional[str] = None
    status: str = "init"  # init, discovery, planning, development, testing, completed
    external_path: Optional[str] = None
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
