import pytest
import uuid
from core.event_bus import EventBus
from core.schemas import SigmaEvent

@pytest.mark.asyncio
async def test_event_bus_history_fallback():
    eb = EventBus()
    eb.use_fallback = True
    
    proj_id = "test-proj-events"
    
    # Kirim 3 event
    for i in range(3):
        evt = SigmaEvent(
            event_id=str(uuid.uuid4()),
            project_id=proj_id,
            event_type="test_event",
            payload={"index": i}
        )
        await eb.publish(proj_id, evt)
        
    events = await eb.get_events(proj_id, limit=2)
    
    # Limit=2 harusnya mengembalikan 2 event terbaru (index 1 dan 2)
    assert len(events) == 2
    assert events[0].payload["index"] == 1
    assert events[1].payload["index"] == 2
