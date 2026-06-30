import json
import logging
import redis.asyncio as redis
from typing import Dict, List, Optional, Any
from datetime import datetime
from core.schemas import ProjectState, TeamConfig, AgentState, AgentMessage, EscalationRequest
from core.constants import AgentName, AgentStatus
from config import settings

logger = logging.getLogger(__name__)

class StateManager:
    """StateManager mengelola state proyek, konfigurasi tim, agent, pesan, dan eskalasi di Redis/In-Memory."""
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.use_fallback = False
        
        # In-memory storage fallback
        self._project_states: Dict[str, Dict[str, Any]] = {}
        self._team_configs: Dict[str, str] = {}
        self._agent_states: Dict[str, Dict[str, Any]] = {}
        self._messages: Dict[str, List[Dict[str, Any]]] = {}
        self._escalations: Dict[str, List[Dict[str, Any]]] = {}

    async def connect(self):
        try:
            self.redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
            await self.redis_client.ping()
            logger.info("StateManager terhubung ke Redis.")
        except Exception as e:
            logger.warning(f"Gagal menghubungkan StateManager ke Redis, menggunakan in-memory fallback. Error: {e}")
            self.use_fallback = True
            self.redis_client = None

    # --- Project State ---
    async def get_project_state(self, project_id: str) -> Optional[ProjectState]:
        key = f"sigma:project:{project_id}:state"
        if not self.use_fallback and self.redis_client:
            try:
                data = await self.redis_client.hgetall(key)
                if data:
                    return ProjectState(
                        project_id=data["project_id"],
                        name=data["name"],
                        description=data.get("description"),
                        status=data.get("status", "init"),
                        created_at=datetime.fromisoformat(data["created_at"]),
                        updated_at=datetime.fromisoformat(data["updated_at"])
                    )
            except Exception as e:
                logger.error(f"Gagal get_project_state dari Redis: {e}")
        
        data = self._project_states.get(project_id)
        if data:
            return ProjectState(**data)
        return None

    async def save_project_state(self, state: ProjectState):
        key = f"sigma:project:{state.project_id}:state"
        state.updated_at = datetime.utcnow()
        data = {
            "project_id": state.project_id,
            "name": state.name,
            "description": state.description or "",
            "status": state.status,
            "created_at": state.created_at.isoformat(),
            "updated_at": state.updated_at.isoformat()
        }
        
        if not self.use_fallback and self.redis_client:
            try:
                await self.redis_client.hset(key, mapping=data)
                return
            except Exception as e:
                logger.error(f"Gagal save_project_state ke Redis: {e}")
        
        self._project_states[state.project_id] = {
            **data,
            "created_at": state.created_at,
            "updated_at": state.updated_at
        }

    # --- Team Config ---
    async def get_team_config(self, project_id: str) -> TeamConfig:
        key = f"sigma:project:{project_id}:team_config"
        if not self.use_fallback and self.redis_client:
            try:
                data = await self.redis_client.get(key)
                if data:
                    return TeamConfig.model_validate_json(data)
            except Exception as e:
                logger.error(f"Gagal get_team_config dari Redis: {e}")
        
        cfg_str = self._team_configs.get(project_id)
        if cfg_str:
            return TeamConfig.model_validate_json(cfg_str)
        return TeamConfig()

    async def save_team_config(self, project_id: str, config: TeamConfig):
        key = f"sigma:project:{project_id}:team_config"
        cfg_str = config.model_dump_json()
        if not self.use_fallback and self.redis_client:
            try:
                await self.redis_client.set(key, cfg_str)
                return
            except Exception as e:
                logger.error(f"Gagal save_team_config ke Redis: {e}")
        
        self._team_configs[project_id] = cfg_str

    def _agent_status_key(self, agent_name: AgentName | str, project_id: Optional[str] = None) -> str:
        value = agent_name.value if isinstance(agent_name, AgentName) else agent_name
        if project_id:
            return f"sigma:project:{project_id}:agent:{value}:status"
        return f"sigma:agent:{value}:status"

    # --- Agent State ---
    async def get_agent_state(self, agent_name: AgentName | str, project_id: Optional[str] = None) -> AgentState:
        key = self._agent_status_key(agent_name, project_id)
        name_str = agent_name.value if isinstance(agent_name, AgentName) else agent_name
        if not self.use_fallback and self.redis_client:
            try:
                data = await self.redis_client.get(key)
                if data:
                    state_dict = json.loads(data)
                    return AgentState(
                        name=AgentName(state_dict["name"]),
                        status=AgentStatus(state_dict["status"]),
                        last_message=state_dict.get("last_message"),
                        token_count=state_dict.get("token_count", 0),
                        updated_at=datetime.fromisoformat(state_dict["updated_at"])
                    )
            except Exception as e:
                logger.error(f"Gagal get_agent_state dari Redis: {e}")
        
        # Fallback local in-memory
        local_key = f"{project_id}:{name_str}" if project_id else name_str
        data = self._agent_states.get(local_key)
        if not data and project_id:
            # Jika scope project belum ada, fallback ke global
            data = self._agent_states.get(name_str)
            
        if data:
            return AgentState(
                name=AgentName(data["name"]),
                status=AgentStatus(data["status"]),
                last_message=data.get("last_message"),
                token_count=data.get("token_count", 0),
                updated_at=data["updated_at"]
            )
        return AgentState(name=AgentName(name_str), status=AgentStatus.IDLE)

    async def save_agent_state(self, state: AgentState, project_id: Optional[str] = None):
        key = self._agent_status_key(state.name, project_id)
        state.updated_at = datetime.utcnow()
        state_dict = {
            "name": state.name.value,
            "status": state.status.value,
            "last_message": state.last_message,
            "token_count": state.token_count,
            "updated_at": state.updated_at.isoformat()
        }
        
        if not self.use_fallback and self.redis_client:
            try:
                await self.redis_client.set(key, json.dumps(state_dict))
                # Juga simpan ke global key sebagai mirror untuk kompatibilitas ke belakang
                global_key = self._agent_status_key(state.name, None)
                await self.redis_client.set(global_key, json.dumps(state_dict))
                return
            except Exception as e:
                logger.error(f"Gagal save_agent_state ke Redis: {e}")
        
        # Simpan ke project scope
        local_key = f"{project_id}:{state.name.value}" if project_id else state.name.value
        self._agent_states[local_key] = {
            **state_dict,
            "updated_at": state.updated_at
        }
        # Juga cerminkan ke global in-memory state
        if project_id:
            self._agent_states[state.name.value] = {
                **state_dict,
                "updated_at": state.updated_at
            }

    # --- Message Log ---
    async def get_messages(self, project_id: str) -> List[AgentMessage]:
        key = f"sigma:messages:{project_id}"
        if not self.use_fallback and self.redis_client:
            try:
                # Membaca dari stream
                stream_data = await self.redis_client.xrange(key)
                messages = []
                for _, entry in stream_data:
                    msg_json = entry.get("data")
                    if msg_json:
                        messages.append(AgentMessage.model_validate_json(msg_json))
                return messages
            except Exception as e:
                logger.error(f"Gagal get_messages dari Redis Stream: {e}")
        
        local_msgs = self._messages.get(project_id, [])
        return [AgentMessage(**msg) for msg in local_msgs]

    async def append_message(self, project_id: str, message: AgentMessage):
        key = f"sigma:messages:{project_id}"
        msg_json = message.model_dump_json()
        if not self.use_fallback and self.redis_client:
            try:
                await self.redis_client.xadd(key, {"data": msg_json})
                return
            except Exception as e:
                logger.error(f"Gagal append_message ke Redis Stream: {e}")
        
        if project_id not in self._messages:
            self._messages[project_id] = []
        self._messages[project_id].append(message.model_dump())

    # --- Escalation ---
    async def get_pending_escalations(self, project_id: str) -> List[EscalationRequest]:
        key = f"sigma:escalation:{project_id}:pending"
        if not self.use_fallback and self.redis_client:
            try:
                # Dapatkan semua list
                items = await self.redis_client.lrange(key, 0, -1)
                escalations = []
                for item in items:
                    escalations.append(EscalationRequest.model_validate_json(item))
                return escalations
            except Exception as e:
                logger.error(f"Gagal get_pending_escalations dari Redis: {e}")
        
        local_escs = self._escalations.get(project_id, [])
        return [EscalationRequest(**esc) for esc in local_escs if not esc.get("resolved")]

    async def add_escalation(self, project_id: str, request: EscalationRequest):
        key = f"sigma:escalation:{project_id}:pending"
        req_json = request.model_dump_json()
        if not self.use_fallback and self.redis_client:
            try:
                await self.redis_client.rpush(key, req_json)
                return
            except Exception as e:
                logger.error(f"Gagal add_escalation ke Redis: {e}")
        
        if project_id not in self._escalations:
            self._escalations[project_id] = []
        self._escalations[project_id].append(request.model_dump())

    async def resolve_escalation(self, project_id: str, escalation_id: str, response: str):
        key = f"sigma:escalation:{project_id}:pending"
        
        # Cari dan update
        if not self.use_fallback and self.redis_client:
            try:
                items = await self.redis_client.lrange(key, 0, -1)
                for index, item in enumerate(items):
                    req = EscalationRequest.model_validate_json(item)
                    if req.id == escalation_id:
                        req.resolved = True
                        req.response = response
                        # Ganti di Redis list
                        await self.redis_client.lset(key, index, req.model_dump_json())
                        # Pindahkan atau biarkan (di-remove jika diselesaikan)
                        # Untuk kemudahan MVP, kita biarkan saja ter-update statusnya atau hapus
                        # Mari hapus jika resolved agar tidak ada di pending list
                        await self.redis_client.lrem(key, 0, item)
                        return req
            except Exception as e:
                logger.error(f"Gagal resolve_escalation di Redis: {e}")
        
        local_escs = self._escalations.get(project_id, [])
        for esc in local_escs:
            if esc["id"] == escalation_id:
                esc["resolved"] = True
                esc["response"] = response
                return EscalationRequest(**esc)
        return None

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
            logger.info("StateManager Redis disconnected.")

state_manager = StateManager()
