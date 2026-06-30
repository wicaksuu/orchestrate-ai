from datetime import datetime
from core.schemas import AgentMessage, MessageMetadata, TeamConfig, ProjectState
from core.constants import MessageType, MessagePriority

def test_team_config_defaults():
    cfg = TeamConfig()
    assert cfg.coder_count == 1
    assert cfg.active_roles["Reviewer"] is True
    assert cfg.models["LeadConsultant"] == "claude-sonnet-4-6"

def test_agent_message_creation():
    meta = MessageMetadata(sender="User", receiver="LeadConsultant")
    msg = AgentMessage(
        id="test-1",
        project_id="proj-1",
        message_type=MessageType.USER,
        content="Halo Lead Consultant",
        priority=MessagePriority.MEDIUM,
        metadata=meta
    )
    assert msg.id == "test-1"
    assert msg.message_type == MessageType.USER
    assert msg.content == "Halo Lead Consultant"
