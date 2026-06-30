import pytest
from core.state_manager import StateManager
from core.schemas import ProjectState, TeamConfig

@pytest.mark.asyncio
async def test_in_memory_state_manager_project_state():
    # Gunakan instansi baru dengan paksa fallback agar terisolasi dari Redis yang sedang jalan
    sm = StateManager()
    sm.use_fallback = True
    
    proj_id = "test-proj-123"
    state = ProjectState(
        project_id=proj_id,
        name="Test Project",
        description="Demo project",
        status="init"
    )
    
    await sm.save_project_state(state)
    retrieved = await sm.get_project_state(proj_id)
    
    assert retrieved is not None
    assert retrieved.name == "Test Project"
    assert retrieved.status == "init"

@pytest.mark.asyncio
async def test_in_memory_state_manager_team_config():
    sm = StateManager()
    sm.use_fallback = True
    
    proj_id = "test-proj-123"
    cfg = TeamConfig(coder_count=3)
    
    await sm.save_team_config(proj_id, cfg)
    retrieved = await sm.get_team_config(proj_id)
    
    assert retrieved.coder_count == 3

@pytest.mark.asyncio
async def test_agent_state_key_regression():
    from core.constants import AgentName, AgentStatus
    from core.schemas import AgentState
    
    sm = StateManager()
    sm.use_fallback = True
    
    state = AgentState(
        name=AgentName.LEAD_CONSULTANT,
        status=AgentStatus.WORKING,
        last_message="hello",
        token_count=100
    )
    
    await sm.save_agent_state(state)
    
    # Ambil menggunakan string nama agent
    retrieved_by_str = await sm.get_agent_state("LeadConsultant")
    assert retrieved_by_str.last_message == "hello"
    assert retrieved_by_str.status == AgentStatus.WORKING
    
    # Ambil menggunakan Enum
    retrieved_by_enum = await sm.get_agent_state(AgentName.LEAD_CONSULTANT)
    assert retrieved_by_enum.last_message == "hello"
    assert retrieved_by_enum.status == AgentStatus.WORKING

@pytest.mark.asyncio
async def test_project_scoped_agent_state():
    from core.constants import AgentName, AgentStatus
    from core.schemas import AgentState
    
    sm = StateManager()
    sm.use_fallback = True
    
    proj_a = "project-A"
    proj_b = "project-B"
    
    state_a = AgentState(
        name=AgentName.CODER,
        status=AgentStatus.WORKING,
        last_message="coding project A",
        token_count=10
    )
    
    state_b = AgentState(
        name=AgentName.CODER,
        status=AgentStatus.IDLE,
        last_message="idle in project B",
        token_count=0
    )
    
    await sm.save_agent_state(state_a, project_id=proj_a)
    await sm.save_agent_state(state_b, project_id=proj_b)
    
    retrieved_a = await sm.get_agent_state(AgentName.CODER, project_id=proj_a)
    retrieved_b = await sm.get_agent_state(AgentName.CODER, project_id=proj_b)
    
    assert retrieved_a.status == AgentStatus.WORKING
    assert retrieved_a.last_message == "coding project A"
    
    assert retrieved_b.status == AgentStatus.IDLE
    assert retrieved_b.last_message == "idle in project B"
