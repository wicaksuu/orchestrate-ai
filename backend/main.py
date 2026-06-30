import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from api.routes import chat, config, agents, logs, project, events
from api.websocket import manager
from core.state_manager import state_manager
from core.event_bus import event_bus
from core.db import database_manager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Memulai SIGMA Backend (Lifespan)...")
    await state_manager.connect()
    await event_bus.connect()
    await database_manager.connect()
    yield
    logger.info("Mematikan SIGMA Backend (Lifespan)...")
    await database_manager.disconnect()
    await state_manager.disconnect()
    await event_bus.disconnect()

app = FastAPI(
    title="SIGMA Orchestrator Platform API",
    description="Backend API untuk SIGMA Multi-Agent platform",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(chat.router, prefix="/api")
app.include_router(config.router, prefix="/api")
app.include_router(agents.router, prefix="/api")
app.include_router(logs.router, prefix="/api")
app.include_router(project.router, prefix="/api")
app.include_router(events.router, prefix="/api")

@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "sigma-backend"}

# WebSocket Endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, project_id: str = "default"):
    """WebSocket endpoint untuk push real-time event ke client."""
    await manager.connect(websocket, project_id)
    try:
        while True:
            # Tetap jaga koneksi tetap hidup dengan mendengarkan ping/pong
            data = await websocket.receive_text()
            # Bisa ditambahkan echo atau penanganan pesan masuk dari client di sini jika diperlukan
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"Error pada WebSocket connection: {e}")
        manager.disconnect(websocket)
