# ARCHITECTURE.md — SIGMA Platform: Technical Architecture Decisions

> Dokumen ini berisi keputusan teknis yang sudah **dilock**. Agent tidak boleh re-decide, berdebat, atau menyimpang dari keputusan di sini. Jika ada alasan kuat untuk mengubah keputusan ini, eskalasi ke Lead Consultant → user — bukan langsung diimplementasi.

---

## 1. SYSTEM OVERVIEW

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                            │
│                    http://localhost:80                           │
└─────────────────────┬───────────────────────────────────────────┘
                      │ HTTP + WebSocket
┌─────────────────────▼───────────────────────────────────────────┐
│                         NGINX :80                               │
│         /api/* → backend:8000    /* → frontend static           │
└──────────┬──────────────────────────────────────────────────────┘
           │                │
┌──────────▼──────┐  ┌──────▼────────────────────────────────────┐
│  FRONTEND       │  │  BACKEND (FastAPI :8000)                   │
│  React + Vite   │  │                                            │
│  Tailwind       │  │  ┌─────────────────────────────────┐      │
│  Framer Motion  │  │  │  Orchestrator                   │      │
│  React Flow     │  │  │  (asyncio event loop)           │      │
│  Zustand        │  │  └──────────┬──────────────────────┘      │
└─────────────────┘  │             │                              │
                     │  ┌──────────▼──────────────────────┐      │
                     │  │  Agent Pool                      │      │
                     │  │  LeadConsultant | Manager        │      │
                     │  │  PromptEngineer | Coder x N      │      │
                     │  │  Reviewer | Tester | Integrator  │      │
                     │  └──────────┬──────────────────────┘      │
                     │             │                              │
                     │  ┌──────────▼──────────────────────┐      │
                     │  │  Event Bus (Redis Pub/Sub)        │      │
                     │  │  State Manager (Redis Hash)       │      │
                     │  │  Message Log (Redis Stream)       │      │
                     │  └──────────┬──────────────────────┘      │
                     │             │                              │
                     │  ┌──────────▼──────────────────────┐      │
                     │  │  Sandbox (subprocess isolated)   │      │
                     │  │  /workspace/sandbox/             │      │
                     │  └─────────────────────────────────┘      │
                     └────────────────────────────────────────────┘
                                   │
                     ┌─────────────▼─────────────┐
                     │     Redis :6379            │
                     │  - Pub/Sub (event bus)     │
                     │  - Hash (project state)    │
                     │  - Stream (message log)    │
                     │  - String (team config)    │
                     └────────────────────────────┘
```

---

## 2. KEPUTUSAN ARSITEKTUR YANG SUDAH DILOCK

### ADR-001: FastAPI sebagai Backend Framework
**Keputusan:** FastAPI (bukan Django, Flask, atau lainnya)
**Alasan:**
- Native async/await — critical untuk orchestrate banyak agent paralel tanpa blocking
- Built-in WebSocket support
- Automatic OpenAPI docs (berguna untuk debugging)
- Typing integration dengan Pydantic

**Konsekuensi:** Semua route handler WAJIB `async def`. Tidak ada synchronous blocking call di event loop.

---

### ADR-002: Redis sebagai Satu-satunya Persistence Layer (MVP)
**Keputusan:** Redis untuk semua state, event, message log — tidak ada SQL database di MVP
**Alasan:**
- Pub/Sub native untuk event bus antar agent
- Sub-millisecond read/write untuk status update yang frequent
- Stream data structure untuk append-only message log
- Cukup untuk kebutuhan single-user MVP
- Zero schema migration overhead

**Redis Key Schema:**
```
sigma:project:{project_id}:state           → Hash (project_state)
sigma:project:{project_id}:team_config     → String (JSON)
sigma:agent:{agent_name}:status            → String (AgentStatus)
sigma:agent:{agent_name}:session           → Hash (history, token_count)
sigma:messages:{project_id}               → Stream (all messages append-only)
sigma:events:{project_id}                 → Stream (UI events append-only)
sigma:escalation:{project_id}:pending     → List (queue eskalasi ke user)
```

**Konsekuensi:** Jika data > RAM Redis, perlu upgrade — tapi ini bukan concern MVP.

---

### ADR-003: WebSocket untuk Real-time Frontend
**Keputusan:** WebSocket native FastAPI (bukan SSE, polling, atau long-polling)
**Alasan:**
- Bidirectional — backend bisa push event ke frontend tanpa request
- Low latency untuk status update animasi
- Satu koneksi WS per browser session, bukan per event

**Pattern:**
```python
# Backend push ke semua connected client saat ada event
async def broadcast_event(event: SigmaEvent):
    for ws in active_connections:
        await ws.send_json(event.model_dump())
```

**Konsekuensi:** Frontend WAJIB implementasi auto-reconnect (lihat `useWebSocket.ts`).

---

### ADR-004: Agent sebagai Coroutine, bukan Thread/Process
**Keputusan:** Semua agent berjalan sebagai `asyncio` coroutine di satu process Python
**Alasan:**
- Lebih ringan dari multi-process (tidak ada IPC overhead)
- Shared memory untuk state (tidak perlu serialisasi antar process)
- I/O-bound workload (API call ke Anthropic) — asyncio optimal untuk ini
- Lebih mudah di-debug dan di-trace

**Konsekuensi:** CPU-bound task (parsing besar, manipulasi file besar) WAJIB pakai `asyncio.run_in_executor()` agar tidak block event loop.

---

### ADR-005: Agent History Management
**Keputusan:** Setiap agent maintain conversation history-nya sendiri (isolated context window)
**Alasan:**
- Isolasi context — Coder tidak perlu baca seluruh history Manager
- Mencegah context window membengkak (yang akan memperlambat dan mahal)
- Sesuai prinsip "send only relevant context"

**Pattern:**
```python
class BaseAgent:
    def __init__(self):
        self.history: list[MessageParam] = []
    
    async def speak(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        response = await self.client.messages.create(
            model=self.model,
            system=self.system_prompt,
            messages=self.history,  # kirim full history agent ini saja
            max_tokens=4000,
        )
        reply = response.content[0].text
        self.history.append({"role": "assistant", "content": reply})
        return reply
```

**Konsekuensi:** Manager bertanggung jawab meringkas dan memilih informasi yang relevan sebelum dikirim ke agent lain (bukan forward raw history).

---

### ADR-006: Sandbox Execution via Subprocess
**Keputusan:** Tester eksekusi kode via `asyncio.create_subprocess_exec()` di direktori `/workspace/sandbox/`
**Alasan:**
- Tidak butuh Docker-in-Docker (lebih simpel)
- Toolchain ARM di-install langsung di backend Docker image
- Isolation via working directory + timeout

**Toolchain yang tersedia di backend image:**
- `arm-none-eabi-gcc` — compiler firmware embedded
- `gcc` — compiler host untuk unit test native
- `make` — build system

**Pattern:**
```python
async def compile_check(source_file: str) -> CompileResult:
    proc = await asyncio.create_subprocess_exec(
        "arm-none-eabi-gcc", "-c", source_file, "-o", "/dev/null",
        cwd="/workspace/sandbox",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    async with asyncio.timeout(SANDBOX_TIMEOUT_SECONDS):
        stdout, stderr = await proc.communicate()
    return CompileResult(
        status="OK" if proc.returncode == 0 else "ERROR",
        errors=stderr.decode(),
    )
```

**Konsekuensi:** Tester TIDAK bisa flash ke hardware beneran — batas eksekusi adalah compile + unit test host-based.

---

### ADR-007: Zustand sebagai Frontend State Manager
**Keputusan:** Zustand (bukan Redux, Context API, atau Recoil)
**Alasan:**
- Minimal boilerplate dibanding Redux
- TypeScript support native
- Tidak butuh Provider wrapper
- Cukup untuk kebutuhan MVP

**Store yang ada:**
- `agentStore` — status semua agent, last message
- `chatStore` — history chat Lead Consultant ↔ user
- `logStore` — communication log semua agent
- `escalationStore` — queue escalation yang pending
- `configStore` — team config (jumlah agent, model, toggle)
- `projectStore` — project list dan active project

---

### ADR-008: React Flow untuk Agent Graph
**Keputusan:** React Flow (bukan D3.js custom, Cytoscape, atau vis.js)
**Alasan:**
- React-native (tidak ada DOM manipulation manual)
- Built-in zoom, pan, dan minimap
- Edge animation support (untuk visualisasi pesan yang sedang dikirim)
- Custom node component support (buat AgentCard)

**Node layout:**
```
[Lead Consultant] ←→ [Manager]
                         │
           ┌─────────────┼─────────────┐
           ▼             ▼             ▼
   [Prompt Engineer]  [Coder 1]   [Coder 2]
                         │
                    [Reviewer]
                         │
                    [Tester]
                         │
                    [Integrator]
                         │
                   [Documenter] (opsional)
```

---

## 3. DEPENDENCY YANG DIIZINKAN

### 3.1 Backend (Python)
```
# DIIZINKAN — tercantum di requirements.txt
anthropic>=0.40.0
fastapi>=0.115.0
uvicorn[standard]>=0.32.0
redis[hiredis]>=5.2.0
pydantic>=2.10.0
pydantic-settings>=2.6.0
python-dotenv>=1.0.0

# DIIZINKAN untuk development/testing
pytest>=8.0.0
pytest-asyncio>=0.24.0
httpx>=0.28.0  # untuk testing FastAPI
black>=24.0.0
ruff>=0.8.0
```

**Menambahkan dependency baru:** WAJIB justifikasi di task brief oleh Prompt Engineer + approval Manager. Coder TIDAK boleh `pip install` sembarangan.

### 3.2 Frontend (npm)
```json
{
  "dependencies": {
    "react": "^18.3.0",
    "react-dom": "^18.3.0",
    "react-flow-renderer": "^11.0.0",
    "framer-motion": "^11.0.0",
    "zustand": "^5.0.0",
    "tailwindcss": "^3.4.0"
  }
}
```

**Menambahkan package baru:** Sama seperti backend — justifikasi dulu, jangan `npm install` sembarangan.

---

## 4. PATTERN YANG WAJIB DIIKUTI

### 4.1 Dependency Injection untuk Agent
```python
# BENAR — inject client dan config dari luar
class Coder(BaseAgent):
    def __init__(
        self,
        instance_id: int,
        anthropic_client: anthropic.AsyncAnthropic,
        event_bus: EventBus,
        state_manager: StateManager,
        model: str,
    ):
        super().__init__(
            name=f"CODER_{instance_id}",
            model=model,
            client=anthropic_client,
        )
        self.event_bus = event_bus
        self.state_manager = state_manager

# SALAH — instantiate dependency di dalam class
class Coder:
    def __init__(self):
        self.client = anthropic.AsyncAnthropic()  # tidak bisa di-mock
```

### 4.2 Event Publication Pattern
```python
# Setiap perubahan status WAJIB publish ke event bus
async def set_status(self, new_status: AgentStatus) -> None:
    prev_status = self.status
    self.status = new_status
    
    await self.event_bus.publish(SigmaEvent(
        event="AGENT_STATUS_CHANGED",
        data={
            "agent": self.name,
            "prev_status": prev_status.value,
            "new_status": new_status.value,
            "message_preview": self._last_message_preview(),
        }
    ))
```

### 4.3 Message Routing (Manager Pattern)
```python
# Manager routing — switch berdasarkan type, bukan if-else bertumpuk
AGENT_HANDLERS: dict[MessageType, Callable] = {
    MessageType.TASK_DONE: handle_task_done,
    MessageType.REVIEW_RESULT: handle_review_result,
    MessageType.TEST_RESULT: handle_test_result,
    MessageType.ESCALATION: handle_escalation,
}

async def route_message(self, message: AgentMessage) -> None:
    handler = AGENT_HANDLERS.get(message.type)
    if handler is None:
        logger.warning("Unhandled message type: %s", message.type)
        return
    await handler(self, message)
```

### 4.4 Pydantic Schema untuk Semua I/O
```python
# Semua message antar agent WAJIB validasi via Pydantic
class AgentMessage(BaseModel):
    msg_id: UUID4
    timestamp: datetime
    from_agent: str
    to_agent: str
    type: MessageType
    priority: MessagePriority = MessagePriority.NORMAL
    payload: dict
    metadata: MessageMetadata

    @field_validator("from_agent", "to_agent")
    def validate_agent_name(cls, v: str) -> str:
        if v not in VALID_AGENT_NAMES and v != "BROADCAST":
            raise ValueError(f"Unknown agent: {v}")
        return v
```

---

## 5. PATTERN YANG DILARANG

| Pattern | Alasan | Alternatif |
|---|---|---|
| Global mutable state (modul-level variable) | Race condition di async | Inject via constructor |
| Synchronous HTTP call (`requests` library) | Block event loop | `httpx` async atau `anthropic` async client |
| Direct file I/O tanpa path validation | Path traversal risk | Gunakan `PathManager` yang validate dalam `WORKSPACE_ROOT` |
| Agent komunikasi langsung ke agent lain (bypass Manager) | Melanggar AGENTS.md hierarchy | Kirim ke Manager, Manager yang route |
| Hardcode agent name sebagai string | Typo risk | Gunakan `AgentName` enum |
| Polling status dari Redis (sisi frontend) | Tidak efisien | WebSocket push dari backend |
| `time.sleep()` di async code | Block event loop | `await asyncio.sleep()` |

---

## 6. SECURITY DECISIONS

### 6.1 Sandbox Path Restriction
```python
WORKSPACE_ROOT = Path(settings.WORKSPACE_ROOT).resolve()

def validate_path(path: str) -> Path:
    """Ensure path is within WORKSPACE_ROOT."""
    resolved = (WORKSPACE_ROOT / path).resolve()
    if not str(resolved).startswith(str(WORKSPACE_ROOT)):
        raise SecurityError(f"Path traversal attempt: {path}")
    return resolved
```

### 6.2 Sandbox Command Whitelist
```python
ALLOWED_COMMANDS = {
    "arm-none-eabi-gcc",
    "arm-none-eabi-objdump",
    "gcc",
    "make",
    "python3",  # untuk test runner
}

def validate_command(command: list[str]) -> None:
    if command[0] not in ALLOWED_COMMANDS:
        raise SecurityError(f"Command not allowed: {command[0]}")
```

### 6.3 API Key
- ANTHROPIC_API_KEY hanya dibaca dari environment variable
- TIDAK PERNAH di-log, di-print, atau masuk ke message antar agent
- TIDAK PERNAH ada di source code, bahkan di test

---

## 7. PERFORMANCE TARGETS

| Metric | Target | Measurement |
|---|---|---|
| WebSocket event latency | < 500ms dari event terjadi sampai UI update | Backend timestamp vs frontend receive |
| Agent status update | < 1 detik setelah status berubah | Event bus round-trip |
| Lead Consultant first response | < 5 detik | API call latency dependent |
| UI render agent card | < 100ms per status change | React profiler |
| Sandbox compile (single file) | < 30 detik | subprocess timer |
| Redis read/write | < 10ms | Redis latency |

---

## 8. FAILURE MODES & HANDLING

| Failure | Handling |
|---|---|
| Anthropic API timeout | Retry dengan exponential backoff (max 3x), lalu set agent status ERROR, eskalasi ke Manager |
| Anthropic API rate limit (429) | Backoff 60 detik, retry, log warning |
| Redis connection lost | Backend crash-loop — Docker restart policy akan handle |
| WebSocket disconnected (frontend) | Auto-reconnect setiap 3 detik, state tetap di Redis |
| Sandbox timeout | Kill subprocess, kirim TIMEOUT result ke Tester, set status ERROR |
| Coder loop > MAX_REVISION_LOOPS | Manager eskalasi ke Lead Consultant |
| Agent stuck THINKING > 120 detik | Manager kirim interrupt, set status BLOCKED, eskalasi |