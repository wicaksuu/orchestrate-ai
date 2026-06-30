# CONVENTIONS.md — SIGMA Platform: Coding Standards & Conventions

> Semua agent WAJIB mengikuti konvensi ini. Reviewer berhak REJECT kode yang melanggar konvensi ini tanpa perlu justifikasi tambahan. Tidak ada pengecualian kecuali ada catatan eksplisit `# CONVENTION_OVERRIDE: [alasan]` di kode.

---

## 1. PRINSIP UTAMA

1. **Explicit over implicit** — Lebih baik verbose dan jelas daripada singkat tapi ambigu
2. **Fail loudly** — Error harus terdeteksi sedini mungkin, jangan silent fail
3. **One thing, one place** — Satu fungsi satu tanggung jawab, tidak ada logika duplikat
4. **Testable by default** — Setiap fungsi yang ditulis Coder harus bisa ditest tanpa modifikasi
5. **No magic numbers** — Semua konstanta harus punya nama dan lokasi sentral

---

## 2. PYTHON CONVENTIONS (Backend)

### 2.1 Formatting
- **Formatter:** `black` (line length 88)
- **Linter:** `ruff`
- **Type hints:** WAJIB di semua fungsi publik — parameter dan return type
- **Docstring:** Google style, WAJIB untuk semua class dan fungsi publik

```python
# BENAR
async def send_message(
    agent_name: str,
    payload: dict,
    priority: MessagePriority = MessagePriority.NORMAL,
) -> MessageResult:
    """Send a structured message to a target agent.

    Args:
        agent_name: Target agent identifier (e.g., "CODER_1").
        payload: Message payload conforming to AGENTS.md section 4.1.
        priority: Message priority level. Defaults to NORMAL.

    Returns:
        MessageResult containing msg_id and delivery status.

    Raises:
        AgentNotFoundError: If agent_name is not in active roster.
        MessageValidationError: If payload does not conform to schema.
    """
    ...

# SALAH
async def send(agent, data, p=None):
    ...
```

### 2.2 Naming
| Entitas | Convention | Contoh |
|---|---|---|
| Variable | `snake_case` | `agent_status`, `task_id` |
| Function/Method | `snake_case` | `get_agent_status()`, `send_message()` |
| Class | `PascalCase` | `LeadConsultant`, `TaskManager` |
| Constant | `UPPER_SNAKE_CASE` | `MAX_RETRY`, `DEFAULT_TIMEOUT` |
| Enum | `PascalCase` + `UPPER` members | `class AgentStatus(Enum): IDLE = "idle"` |
| Private method | `_single_underscore` | `_validate_payload()` |
| Module | `snake_case` | `state_manager.py`, `event_bus.py` |

### 2.3 Error Handling
```python
# BENAR — custom exception, pesan informatif
class AgentNotFoundError(SigmaBaseError):
    def __init__(self, agent_name: str):
        super().__init__(f"Agent '{agent_name}' not found in active roster")
        self.agent_name = agent_name

# BENAR — tangkap spesifik, log, re-raise atau handle
try:
    result = await agent.execute(task)
except AgentNotFoundError as e:
    logger.error("Agent not found: %s", e.agent_name)
    raise
except AnthropicAPIError as e:
    logger.warning("API error (retry %d): %s", retry_count, str(e))
    # handle retry logic

# SALAH — tangkap semua, buang error
try:
    result = await agent.execute(task)
except:
    pass
```

### 2.4 Async
- Semua I/O operation WAJIB `async/await` — tidak ada blocking call di event loop
- Gunakan `asyncio.gather()` untuk operasi paralel antar agent
- Timeout WAJIB untuk semua external call:
```python
# BENAR
async with asyncio.timeout(settings.SANDBOX_TIMEOUT_SECONDS):
    result = await sandbox.execute(command)

# SALAH
result = await sandbox.execute(command)  # bisa hang selamanya
```

### 2.5 Logging
```python
import logging
logger = logging.getLogger(__name__)

# Format: level | module | pesan
logger.debug("Agent %s transitioning: %s → %s", agent_name, prev, new)
logger.info("Task %s assigned to %s", task_id, agent_name)
logger.warning("Retry %d/%d for task %s", attempt, max_retry, task_id)
logger.error("Agent %s failed: %s", agent_name, error_msg, exc_info=True)

# DILARANG: print() untuk logging di production code
print("debug")  # TIDAK BOLEH
```

### 2.6 Import Order
```python
# 1. Standard library
import asyncio
import json
from enum import Enum
from typing import Optional

# 2. Third-party
import anthropic
import redis.asyncio as redis
from fastapi import WebSocket

# 3. Internal (absolute path dari root)
from core.agent import BaseAgent
from core.event_bus import EventBus
from api.schemas import MessageSchema
```

### 2.7 Constants
```python
# BENAR — semua di config.py atau constants.py
MAX_REVISION_LOOPS: int = 3
DEFAULT_MODEL: str = "claude-sonnet-4-6"
AGENT_STATUS_TTL: int = 86400  # seconds

# SALAH — magic number di tengah kode
if retry_count > 3:  # 3 dari mana?
    ...
```

---

## 3. TYPESCRIPT/REACT CONVENTIONS (Frontend)

### 3.1 Formatting
- **Formatter:** Prettier (default config)
- **Linter:** ESLint + `eslint-config-react-app`
- **Language:** TypeScript strict mode (`"strict": true` di tsconfig)

### 3.2 Naming
| Entitas | Convention | Contoh |
|---|---|---|
| Component | `PascalCase` | `AgentCard`, `ChatWindow` |
| Hook | `camelCase` dengan prefix `use` | `useWebSocket`, `useAgentState` |
| Util function | `camelCase` | `formatTimestamp()`, `parseMessage()` |
| Constant | `UPPER_SNAKE_CASE` | `WS_RECONNECT_INTERVAL` |
| Type/Interface | `PascalCase` dengan suffix Type/Props | `AgentStatusType`, `ChatBubbleProps` |
| CSS class | `kebab-case` (Tailwind utilities saja) | `agent-card`, `status-badge` |
| File component | `PascalCase.tsx` | `AgentCard.tsx` |
| File hook | `camelCase.ts` | `useWebSocket.ts` |

### 3.3 Component Structure
```tsx
// URUTAN WAJIB dalam file component:
// 1. Imports
// 2. Types/Interfaces
// 3. Constants (jika ada)
// 4. Component function
// 5. Subcomponents kecil (jika ada, letakkan di bawah parent)
// 6. Export

import { useState, useEffect } from "react"
import { motion } from "framer-motion"
import type { AgentStatus } from "@/types"

interface AgentCardProps {
  agentName: string
  status: AgentStatus
  lastMessage: string
  tokenCount: number
  onDetailClick: (agentName: string) => void
}

const STATUS_COLORS: Record<AgentStatus, string> = {
  IDLE: "bg-gray-400",
  THINKING: "bg-yellow-400",
  WORKING: "bg-blue-500",
  // ...
}

export function AgentCard({
  agentName,
  status,
  lastMessage,
  tokenCount,
  onDetailClick,
}: AgentCardProps) {
  // hooks dulu, baru logic
  const [isExpanded, setIsExpanded] = useState(false)

  // derived values
  const colorClass = STATUS_COLORS[status]

  // handlers
  const handleDetailClick = () => onDetailClick(agentName)

  return (
    <motion.div className="...">
      {/* JSX */}
    </motion.div>
  )
}
```

### 3.4 State Management (Zustand)
```typescript
// store/agentStore.ts
interface AgentStore {
  agents: Record<string, AgentState>
  updateAgentStatus: (name: string, status: AgentStatus) => void
  addMessage: (msg: AgentMessage) => void
}

// BENAR — action di dalam store, bukan di component
export const useAgentStore = create<AgentStore>((set) => ({
  agents: {},
  updateAgentStatus: (name, status) =>
    set((state) => ({
      agents: {
        ...state.agents,
        [name]: { ...state.agents[name], status },
      },
    })),
}))

// SALAH — manipulasi state langsung di component
const [agents, setAgents] = useState({})
```

### 3.5 WebSocket Hook Pattern
```typescript
// WAJIB: auto-reconnect, cleanup on unmount
export function useWebSocket(url: string) {
  const [isConnected, setIsConnected] = useState(false)
  
  useEffect(() => {
    const ws = new WebSocket(url)
    ws.onopen = () => setIsConnected(true)
    ws.onclose = () => {
      setIsConnected(false)
      setTimeout(() => reconnect(), WS_RECONNECT_INTERVAL)
    }
    ws.onmessage = (event) => handleEvent(JSON.parse(event.data))
    
    return () => ws.close()  // cleanup WAJIB
  }, [url])
}
```

---

## 4. JSON COMMUNICATION CONVENTIONS

### 4.1 Field Naming
- Semua field: `snake_case`
- Timestamp: ISO-8601 string (`"2026-01-01T10:00:00Z"`)
- ID: UUID v4 string
- Status/Enum: `UPPER_SNAKE_CASE` string
- Boolean: prefix `is_` atau `has_` (`is_blocking`, `has_error`)

### 4.2 Null Handling
```json
// BENAR — field opsional yang tidak ada nilainya: null eksplisit
{ "physical_request": null, "error": null }

// SALAH — omit field yang tidak ada nilainya
{ }  // tidak jelas apakah field tidak ada atau tidak dikirim
```

### 4.3 Error Payload
```json
{
  "error": {
    "code": "COMPILE_ERROR",
    "message": "undefined reference to 'delay_ms'",
    "file": "main.c",
    "line": 42,
    "raw_output": "..."
  }
}
```

### 4.4 Ukuran Payload
- Payload JSON antar agent: maksimum **50KB per message**
- Jika kode yang dikirim > 50KB: simpan ke file di workspace, kirim path-nya saja
- Raw compile output > 10KB: tulis ke file log, kirim summary + path

---

## 5. FILE & FOLDER CONVENTIONS

### 5.1 Workspace Structure
```
/workspace/
├── tasks/{task_id}/
│   ├── brief.md          # snake_case, lowercase
│   ├── code/             # semua file kode dari Coder
│   ├── review.json       # satu file per review cycle
│   └── test_result.json  # satu file per test run
└── deliverables/
    ├── src/              # source code final
    ├── tests/            # test files final
    └── README.md         # dokumentasi final
```

### 5.2 File Naming
- Source file: `snake_case.{ext}` (Python), `PascalCase.tsx` (React component), `camelCase.ts` (utils/hooks)
- Config file: `snake_case.json` / `snake_case.yaml`
- Log file: `{agent}_{task_id}_{timestamp}.log`
- TIDAK BOLEH: spasi, karakter khusus, atau uppercase di nama file backend/config

### 5.3 Kode yang Ditulis Coder
```
tasks/{task_id}/code/
├── {module_name}.c       # implementasi (embedded C)
├── {module_name}.h       # header
└── test_{module_name}.c  # unit test (WAJIB disertakan)
```

---

## 6. GIT CONVENTIONS (untuk Integrator)

### 6.1 Commit Message Format
```
{type}({scope}): {deskripsi singkat}

{body opsional}

Task-ID: {task_id}
Agent: {INTEGRATOR | CODER_1 | ...}
```

Type yang valid: `feat`, `fix`, `test`, `refactor`, `docs`, `chore`

Contoh:
```
feat(timing): implement fixed-point ignition timing calculator

Implements Q15 fixed-point arithmetic for timing advance calculation.
Range: 0-40 degrees, resolution: 0.03 degrees.

Task-ID: task-abc123
Agent: CODER_1
```

### 6.2 Branch (jika dipakai)
- `main` — hanya deliverable yang sudah lolos semua test
- `task/{task_id}` — working branch per task

---

## 7. DOKUMENTASI KODE

### 7.1 Header File (untuk C/embedded)
```c
/**
 * @file    timing_calc.c
 * @brief   Fixed-point ignition timing calculator
 * @details Implements advance timing lookup with Q15 arithmetic.
 *          Range: 0-40 degrees. Input: RPM (0-15000), MAP (0-100 kPa)
 *
 * Task-ID: task-abc123
 * Agent:   CODER_1
 * Reviewed-by: REVIEWER (approved)
 */
```

### 7.2 Fungsi (C)
```c
/**
 * @brief  Calculate ignition advance angle from RPM and MAP.
 * @param  rpm   Engine speed in RPM (valid range: 0-15000)
 * @param  map   Manifold pressure in kPa (valid range: 0-100)
 * @return Advance angle in Q15 fixed-point (1.0 = 1 degree)
 * @retval TIMING_ERR_RANGE if inputs out of valid range
 */
int16_t timing_calc_advance(uint16_t rpm, uint8_t map);
```

### 7.3 Fungsi (Python)
Lihat section 2.1 — Google style docstring, wajib.

### 7.4 Inline Comment
```python
# BENAR — jelaskan KENAPA, bukan APA
# Retry dengan exponential backoff karena Anthropic API rate limit
# bisa terjadi saat banyak Coder berjalan paralel
await asyncio.sleep(2 ** retry_count)

# SALAH — jelaskan APA (sudah jelas dari kode)
# Tunggu sebentar
await asyncio.sleep(2 ** retry_count)
```

---

## 8. TESTING CONVENTIONS

### 8.1 Unit Test Naming
```python
# Pattern: test_{fungsi_yang_ditest}_{kondisi}_{expected_result}
def test_timing_calc_advance_at_max_rpm_returns_max_advance():
    ...

def test_timing_calc_advance_with_invalid_rpm_raises_range_error():
    ...
```

### 8.2 Test Structure (AAA Pattern)
```python
def test_send_message_to_valid_agent_returns_success():
    # Arrange
    agent = MockAgent("CODER_1")
    payload = build_test_payload()

    # Act
    result = send_message("CODER_1", payload)

    # Assert
    assert result.status == "DELIVERED"
    assert result.msg_id is not None
```

### 8.3 Coverage Minimum
- Fungsi publik: **100% dipanggil** di test
- Branch coverage: **minimal 80%**
- Edge case wajib ditest: nilai minimum, nilai maksimum, input invalid

---

## 9. LARANGAN ABSOLUT

Hal-hal berikut adalah BLOCKER di code review, tidak ada pengecualian:

1. `TODO`, `FIXME`, `HACK` di kode yang dikirim ke Reviewer — selesaikan dulu atau buat task baru
2. Credential/API key hardcoded di source code
3. `print()` atau `console.log()` yang tertinggal di production code
4. Fungsi lebih dari 50 baris (Python) atau 80 baris (C) tanpa justifikasi
5. Nested `if` lebih dari 3 level — refactor ke fungsi terpisah
6. Catch semua exception tanpa handling spesifik
7. File kode tanpa unit test yang menyertainya
8. Import wildcard: `from module import *`
9. Mutable default argument di Python: `def f(data=[]):`
10. `any` type di TypeScript tanpa komentar justifikasi