import asyncio
from core.state_manager import state_manager
from config import settings

async def main():
    await state_manager.connect()
    # Find the latest project id or we can just pull from the latest messages if we don't know the exact project id.
    # The log showed eb12d46a-3e6e-4b2c-8dbc-a1bdc059d23a
    project_id = "eb12d46a-3e6e-4b2c-8dbc-a1bdc059d23a"
    msgs = await state_manager.get_messages(project_id)
    for msg in msgs:
        if msg.metadata and msg.metadata.sender in ("Manager", "UiUxDesigner"):
            print(f"[{msg.metadata.sender}]: {msg.content[:150]}...")
    await state_manager.disconnect()

asyncio.run(main())
