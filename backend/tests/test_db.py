import pytest

from core.db import DatabaseManager
from core.schemas import AgentAISettingUpdate


@pytest.mark.asyncio
async def test_agent_ai_setting_fallback_encrypts_and_masks_key():
    manager = DatabaseManager()
    manager.use_fallback = True

    saved = await manager.save_agent_ai_setting(
        "project-1",
        AgentAISettingUpdate(
            agent_name="LeadConsultant",
            provider="openai",
            model="gpt-5.5",
            api_key="secret-token",
        ),
    )

    assert saved.agent_name == "LeadConsultant"
    assert saved.provider == "openai"
    assert saved.model == "gpt-5.5"
    assert saved.api_key_configured is True

    public_settings = await manager.get_agent_ai_settings("project-1")
    assert public_settings[0].api_key_configured is True
    assert not hasattr(public_settings[0], "api_key")

    runtime = await manager.get_agent_ai_runtime("project-1", "LeadConsultant")
    assert runtime == {
        "provider": "openai",
        "model": "gpt-5.5",
        "api_key": "secret-token",
    }
