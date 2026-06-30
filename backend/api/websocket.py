import logging
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
from core.schemas import SigmaEvent
from core.event_bus import event_bus

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Mengelola koneksi WebSocket aktif untuk menerima real-time update."""
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket, project_id: str):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client terhubung ke project: {project_id}")
        
        # Setup listener otomatis jika pertama kali
        event_bus.subscribe(project_id, self.broadcast_event)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info("WebSocket client terputus.")

    async def broadcast_event(self, event: SigmaEvent):
        """Kirim event ke seluruh client yang terhubung."""
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(event.model_dump_json())
            except Exception as e:
                logger.error(f"Gagal mengirim pesan ke WS: {e}")
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

manager = ConnectionManager()
