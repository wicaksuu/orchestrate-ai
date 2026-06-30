import asyncio
import json
import logging
import redis.asyncio as redis
from typing import Callable, Dict, List, Any, Optional
from core.schemas import SigmaEvent
from config import settings

logger = logging.getLogger(__name__)

class EventBus:
    """EventBus menangani pub/sub event menggunakan Redis atau In-Memory fallback."""
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.use_fallback = False
        self._subscribers: Dict[str, List[Callable]] = {}
        # In-memory event history fallback
        self._local_event_history: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            # Uji koneksi
            await self.redis_client.ping()
            logger.info("EventBus terhubung ke Redis.")
        except Exception as e:
            logger.warning(f"Gagal menghubungkan EventBus ke Redis, menggunakan in-memory fallback. Error: {e}")
            self.use_fallback = True
            self.redis_client = None

    async def publish(self, project_id: str, event: SigmaEvent):
        channel = f"sigma:events:{project_id}"
        event_json = event.model_dump_json()
        
        # Simpan ke in-memory history selalu untuk mempermudah unit test dan fallback
        if project_id not in self._local_event_history:
            self._local_event_history[project_id] = []
        self._local_event_history[project_id].append(event.model_dump())

        if not self.use_fallback and self.redis_client:
            try:
                await self.redis_client.publish(channel, event_json)
                # Juga simpan ke stream
                await self.redis_client.xadd(channel, {"data": event_json})
                # Tetap panggil local subscriber agar connected WebSocket menerima event
                await self._publish_local(channel, event)
            except Exception as e:
                logger.error(f"Gagal publish ke Redis: {e}. Fallback ke in-memory.")
                await self._publish_local(channel, event)
        else:
            await self._publish_local(channel, event)

    async def get_events(self, project_id: str, limit: int = 100) -> List[SigmaEvent]:
        """Mengambil riwayat event untuk proyek."""
        channel = f"sigma:events:{project_id}"
        if not self.use_fallback and self.redis_client:
            try:
                # Ambil dari Redis Stream (xrevrange mengambil terbaru dahulu)
                stream_data = await self.redis_client.xrevrange(channel, count=limit)
                events = []
                for _, entry in stream_data:
                    evt_json = entry.get("data")
                    if evt_json:
                        events.append(SigmaEvent.model_validate_json(evt_json))
                # Urutkan kembali dari yang terlama ke terbaru agar logis untuk UI
                events.reverse()
                return events
            except Exception as e:
                logger.error(f"Gagal get_events dari Redis Stream: {e}. Menggunakan fallback.")

        local_evts = self._local_event_history.get(project_id, [])
        # Ambil limit terbaru
        tail_evts = local_evts[-limit:] if len(local_evts) > limit else local_evts
        return [SigmaEvent(**evt) for evt in tail_evts]

    async def _publish_local(self, channel: str, event: SigmaEvent):
        if channel in self._subscribers:
            for cb in self._subscribers[channel]:
                if asyncio.iscoroutinefunction(cb):
                    asyncio.create_task(cb(event))
                else:
                    cb(event)

    def subscribe(self, project_id: str, callback: Callable):
        channel = f"sigma:events:{project_id}"
        if channel not in self._subscribers:
            self._subscribers[channel] = []
        self._subscribers[channel].append(callback)
        logger.info(f"Subscribed local listener ke channel: {channel}")

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("EventBus Redis disconnected.")

event_bus = EventBus()
