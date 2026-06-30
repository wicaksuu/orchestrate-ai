# PRD.md — Multi-Agent Development Platform
## Product Requirements Document v1.0

---

## 1. PRODUCT OVERVIEW

### 1.1 Nama Produk
**SIGMA** — *Supervised Intelligent Group of Multi-Agents*

### 1.2 Deskripsi Singkat
Platform orkestasi multi-agent berbasis LLM yang mengeksekusi proyek software/firmware kompleks secara otonom layaknya tim profesional, dengan antarmuka visual real-time dan komunikasi natural-language antara user dan Lead Consultant dalam Bahasa Indonesia.

### 1.3 Problem Statement
Proyek software/firmware kompleks membutuhkan:
- Perencanaan terstruktur
- Implementasi modular yang bisa paralel
- Review & QA yang objektif
- Eksekusi test yang nyata (bukan simulasi)
- Koordinasi antara semua role di atas

Satu AI agent dalam satu sesi tidak optimal untuk semua ini — konteks membengkak, switching cost tinggi, bias reviewer (karena reviewer adalah orang yang sama yang nulis kode), dan tidak bisa paralel. SIGMA menjawab semua masalah ini dengan arsitektur multi-agent yang terstruktur.

### 1.4 Target User
- Wicaksu (primary) — developer/engineer yang mengerjakan proyek kompleks (firmware embedded, full-stack, tooling, dll) dan ingin team AI yang bisa dikasih task lalu eksekusi sampai selesai
- Desain harus generalizable — proyek pertama CDI YZ125 STM32H562, tapi platform harus bisa dipakai untuk jenis proyek lain

---

## 2. GOALS & SUCCESS CRITERIA

### 2.1 Goals
1. User bisa jelaskan proyek ke Lead Consultant → tim mulai kerja → deliverable selesai tanpa user perlu turun tangan kecuali keputusan kritis dan aksi fisik
2. User bisa pantau percakapan dan status tiap agent secara real-time di web UI
3. User bisa konfigurasi komposisi tim melalui UI (jumlah agent, model per agent, role aktif/nonaktif)
4. Tester agent benar-benar menjalankan kode (compile, unit test) bukan sekadar analisis

### 2.2 Success Criteria (MVP)
- [ ] Lead Consultant bisa lakukan discovery dan rekomendasikan tim dalam satu conversation
- [ ] Tim bisa menyelesaikan satu modul kode (± 200-500 baris) end-to-end tanpa intervensi user
- [ ] Compile check dan unit test berjalan via subprocess di sandbox
- [ ] Semua event agent (status change, pesan, escalation) tampil di UI < 2 detik setelah terjadi
- [ ] User bisa approve/reject/respond dari UI tanpa perlu akses terminal
- [ ] Semua proses berjalan di Docker — satu perintah `docker compose up` untuk start platform

---

## 3. FITUR — MVP (v1.0)

### 3.1 Lead Consultant Chat Interface
- Chat window dedicated antara user dan Lead Consultant
- Lead Consultant support conversation multi-turn dengan memory session
- Lead Consultant mampu:
  - Discovery: tanya goal, scope, constraint, output yang diharapkan, deadline
  - Rekomendasikan komposisi tim + trade-off (token cost, waktu, risiko)
  - Minta approval user sebelum eksekusi dimulai
  - Update status tim dalam Bahasa Indonesia (bukan raw log)
  - Eskalasi keputusan kritis dan physical request ke user via chat
  - Laporan final project

### 3.2 Agent Visual Dashboard
**Layout:** Split panel — kiri: chat Lead Consultant, kanan: agent status panel

**Agent cards (satu card per agent aktif):**
- Nama agent + role icon
- Status badge dengan animasi sesuai AGENTS.md section 5:
  - IDLE: abu-abu, static
  - THINKING: kuning, pulse lambat (CSS pulse 2s)
  - WORKING: biru, pulse cepat (CSS pulse 0.8s)
  - WAITING_REVIEW: ungu, ping
  - WAITING_USER_INPUT: oranye, bounce + banner global notification
  - DONE: hijau solid
  - BLOCKED: merah, shake + alert
  - ERROR: merah tua + alert banner merah di atas page
- Last message preview (50 karakter terakhir dari output agent)
- Token count estimate untuk session agent tersebut
- Tombol "Lihat Detail" → expand log percakapan penuh agent

**Flow visualization:**
- Garis koneksi antar node agent (React Flow)
- Garis menyala/animasi saat message sedang dikirim dari agent A ke B
- Node posisi: Lead Consultant (kiri), Manager (tengah-atas), agent lain (kanan/bawah sesuai hierarchy)

### 3.3 Konigurasi Tim via UI
**Config panel (bisa dibuka via sidebar atau modal):**
- Slider jumlah Coder (1-5)
- Toggle on/off tiap role (Documenter, Integrator, dll)
- Dropdown model per agent (claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001)
- Tombol "Rekomendasikan ke Lead Consultant" — kirim konfigurasi yang diubah user ke Lead Consultant buat dievaluasi
- Konfigurasi tersimpan di `team_config.json` dan persist antar session

**Catatan:** Konfigurasi hanya aktif setelah disetujui oleh user melalui conversation Lead Consultant (bukan langsung apply dari UI saja)

### 3.4 Real-time Agent Communication Log
- Tab atau panel terpisah: "Communication Log"
- Tampilkan semua message antar agent dalam format timeline (sender → receiver, timestamp, type, preview content)
- Filter by: agent, message type, time range
- Search by keyword
- Warna berbeda per agent (konsisten dengan warna card di dashboard)
- Toggle "Raw JSON" vs "Human-readable summary" per message

### 3.5 Escalation & Approval System
- Saat ada `WAITING_USER_INPUT`, muncul **alert banner oranye** di atas seluruh halaman
- Alert menampilkan:
  - Siapa yang butuh input (via Lead Consultant)
  - Deskripsi yang dibutuhkan (dalam Bahasa Indonesia)
  - Pilihan aksi: tombol quick-respond (jika ada opsi terbatas) ATAU input text (jika butuh jawaban bebas)
  - Timer countdown jika ada timeout
- Pipeline benar-benar pause sampai user respond — bukan skip otomatis
- History semua escalation dan response user tercatat di log

### 3.6 Sandbox Execution Environment
- Direktori `/workspace/sandbox/` untuk eksekusi Tester
- Tester bisa run:
  - `arm-none-eabi-gcc` untuk compile check firmware target
  - `gcc` untuk compile dan run unit test native (host-based)
  - Custom test runner berdasarkan jenis proyek (didefinisikan per-project)
- Output compile dan test di-stream real-time ke UI (bukan tunggu selesai)
- Timeout per eksekusi: configurable, default 120 detik

### 3.7 Project State & Persistence
- Seluruh state tersimpan di Redis:
  - Status semua agent
  - History message antar agent
  - Konfigurasi tim aktif
  - Event queue untuk UI
- Deliverable tersimpan di volume Docker yang di-mount
- Platform bisa restart tanpa kehilangan state proyek yang sedang berjalan
- Session bisa di-resume jika koneksi browser putus

### 3.8 WORKSPACE_ROOT Per-Project
- Tiap project punya workspace directory sendiri
- User bisa create project baru dari UI (nama project, deskripsi singkat)
- Switching antar project tersedia (tapi hanya satu project yang bisa running eksekusi aktif pada satu waktu)

---

## 4. FITUR — V2 (FUTURE, BUKAN MVP)

| Fitur | Alasan ditunda |
|---|---|
| Multi-project concurrent execution | Kompleksitas resource management tinggi |
| User authentication / multi-user | Cukup single-user untuk saat ini |
| Git integration (auto-commit per milestone) | Nice-to-have, bukan blocker |
| Notification push (email/Telegram) saat butuh input user | Bisa ditambah modular setelah MVP |
| Plugin system untuk tambah agent role baru via UI | Butuh abstraksi lebih lanjut |
| Cost dashboard (total token terpakai + estimasi biaya) | Prioritas rendah |
| Export conversation log ke PDF/Markdown | Nice-to-have |
| Drag-and-drop node untuk re-route communication path | Sangat kompleks, nilai tambah terbatas |

---

## 5. ARSITEKTUR TEKNIS

### 5.1 Stack

| Layer | Teknologi | Alasan |
|---|---|---|
| **Backend** | Python 3.11 + FastAPI | Ekosistem AI terbaik, async native, WebSocket built-in |
| **AI SDK** | `anthropic` Python SDK | Target model Claude API |
| **Real-time** | WebSocket (FastAPI native) | Push event ke frontend tanpa polling, low latency |
| **Event Bus** | Redis Pub/Sub | Decoupled komunikasi antar agent + persistensi state |
| **Database** | Redis (primary) | State, queue, history — cukup untuk kebutuhan ini, no SQL overhead |
| **Frontend** | React 18 + Vite | Fast build, ekosistem matang |
| **UI Styling** | Tailwind CSS | Utility-first, cepat |
| **Animation** | Framer Motion | Animasi status card yang smooth |
| **Graph** | React Flow | Node-graph agent visualization, interaktif |
| **Container** | Docker + Docker Compose | Satu perintah setup, reproducible |
| **Reverse Proxy** | Nginx (dalam Docker) | Serve React build + proxy ke FastAPI |
| **Sandbox** | Docker volume + subprocess | Isolasi eksekusi Tester |

### 5.2 Service Architecture (Docker Compose)

```
┌─────────────────────────────────────────────────────┐
│                    docker-compose                    │
│                                                      │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐  │
│  │  nginx   │    │ backend  │    │    redis     │  │
│  │  :80     │───►│ :8000    │───►│    :6379     │  │
│  │ (React)  │    │ FastAPI  │    │  (state+bus) │  │
│  └──────────┘    └──────────┘    └──────────────┘  │
│                       │                              │
│              ┌────────┴────────┐                     │
│              ▼                 ▼                     │
│        /workspace/        /sandbox/                  │
│        (volume mount)     (volume mount)             │
└─────────────────────────────────────────────────────┘
```

### 5.3 Backend Module Structure

```
backend/
├── main.py                     # FastAPI app entry point
├── config.py                   # Settings, env vars, model config
├── core/
│   ├── agent.py                # Base Agent class: API call, history, status
│   ├── agents/
│   │   ├── lead_consultant.py  # LeadConsultant agent implementation
│   │   ├── manager.py          # Manager agent implementation
│   │   ├── prompt_engineer.py  # PromptEngineer agent implementation
│   │   ├── coder.py            # Coder agent implementation
│   │   ├── reviewer.py         # Reviewer agent implementation
│   │   ├── tester.py           # Tester agent + subprocess execution
│   │   ├── integrator.py       # Integrator agent implementation
│   │   └── documenter.py       # Documenter agent implementation
│   ├── orchestrator.py         # Task routing, team lifecycle management
│   ├── event_bus.py            # Redis pub/sub wrapper
│   ├── state_manager.py        # project_state.json + Redis state ops
│   └── sandbox.py              # Subprocess execution + streaming output
├── api/
│   ├── routes/
│   │   ├── chat.py             # POST /api/chat (user → Lead Consultant)
│   │   ├── config.py           # GET/POST /api/config (team config)
│   │   ├── project.py          # GET/POST /api/project (project management)
│   │   ├── agents.py           # GET /api/agents (agent status list)
│   │   └── logs.py             # GET /api/logs (communication log)
│   └── websocket.py            # WS /ws (real-time event push ke frontend)
├── prompts/
│   ├── lead_consultant.md      # System prompt Lead Consultant
│   ├── manager.md              # System prompt Manager
│   ├── prompt_engineer.md      # System prompt Prompt Engineer
│   ├── coder.md                # System prompt Coder
│   ├── reviewer.md             # System prompt Reviewer
│   ├── tester.md               # System prompt Tester
│   ├── integrator.md           # System prompt Integrator
│   └── documenter.md           # System prompt Documenter
└── requirements.txt
```

### 5.4 Frontend Module Structure

```
frontend/
├── src/
│   ├── App.jsx                 # Root component, layout
│   ├── components/
│   │   ├── chat/
│   │   │   ├── ChatWindow.jsx  # Lead Consultant chat interface
│   │   │   ├── ChatBubble.jsx  # Individual message bubble
│   │   │   └── ChatInput.jsx   # Input box + send button
│   │   ├── dashboard/
│   │   │   ├── AgentCard.jsx   # Single agent card dengan status animasi
│   │   │   ├── AgentGrid.jsx   # Grid semua agent cards
│   │   │   ├── AgentGraph.jsx  # React Flow node-graph visualization
│   │   │   └── StatusBadge.jsx # Badge dengan animasi per status
│   │   ├── logs/
│   │   │   ├── CommLog.jsx     # Communication log timeline
│   │   │   ├── LogEntry.jsx    # Single log entry (dengan toggle raw/human)
│   │   │   └── LogFilter.jsx   # Filter & search controls
│   │   ├── config/
│   │   │   ├── TeamConfig.jsx  # Config panel (slider, toggle, dropdown)
│   │   │   └── ModelSelect.jsx # Model selector per agent
│   │   ├── escalation/
│   │   │   ├── EscalationBanner.jsx  # Alert banner oranye
│   │   │   └── EscalationModal.jsx   # Detail + response input
│   │   └── common/
│   │       ├── Layout.jsx
│   │       └── Navbar.jsx
│   ├── hooks/
│   │   ├── useWebSocket.js     # WebSocket connection + auto-reconnect
│   │   ├── useAgentState.js    # Agent status state management
│   │   └── useEscalation.js    # Escalation queue management
│   ├── store/
│   │   └── index.js            # Zustand store (global state)
│   └── styles/
│       └── index.css           # Tailwind directives + custom animations
├── index.html
├── vite.config.js
├── tailwind.config.js
└── package.json
```

### 5.5 WebSocket Event Schema
Semua real-time event dari backend ke frontend menggunakan format:

```json
{
  "event": "AGENT_STATUS_CHANGED | NEW_MESSAGE | ESCALATION | COMPILE_OUTPUT | TEST_RESULT | PROJECT_DONE",
  "timestamp": "ISO-8601",
  "data": { }
}
```

Contoh event `AGENT_STATUS_CHANGED`:
```json
{
  "event": "AGENT_STATUS_CHANGED",
  "timestamp": "2026-01-01T10:00:00Z",
  "data": {
    "agent": "CODER_1",
    "prev_status": "THINKING",
    "new_status": "WORKING",
    "message_preview": "Implementing fixed-point multiply..."
  }
}
```

Contoh event `NEW_MESSAGE`:
```json
{
  "event": "NEW_MESSAGE",
  "timestamp": "2026-01-01T10:00:01Z",
  "data": {
    "msg_id": "uuid",
    "from": "REVIEWER",
    "to": "MANAGER",
    "type": "REVIEW",
    "preview": "REJECTED: 1 BLOCKER found at timing_calc.c:42",
    "full_payload": { }
  }
}
```

---

## 6. ENVIRONMENT & CONFIGURATION

### 6.1 Environment Variables (`.env`)
```env
# Anthropic API
ANTHROPIC_API_KEY=sk-ant-...

# Redis
REDIS_URL=redis://redis:6379

# Workspace
WORKSPACE_ROOT=/workspace
SANDBOX_DIR=/workspace/sandbox

# Backend
BACKEND_PORT=8000
CORS_ORIGINS=http://localhost,http://localhost:80

# Agent Models (override per-agent via UI, ini default)
MODEL_LEAD_CONSULTANT=claude-opus-4-6
MODEL_MANAGER=claude-sonnet-4-6
MODEL_PROMPT_ENGINEER=claude-sonnet-4-6
MODEL_CODER=claude-sonnet-4-6
MODEL_REVIEWER=claude-sonnet-4-6
MODEL_TESTER=claude-sonnet-4-6
MODEL_INTEGRATOR=claude-haiku-4-5-20251001
MODEL_DOCUMENTER=claude-haiku-4-5-20251001

# Limits
MAX_CODER_INSTANCES=5
MAX_REVISION_LOOPS=3
SANDBOX_TIMEOUT_SECONDS=120

# Toolchain (untuk Tester embedded firmware)
ARM_TOOLCHAIN_PATH=/usr/bin/arm-none-eabi-gcc
```

### 6.2 Docker Compose
```yaml
services:
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    restart: unless-stopped

  backend:
    build: ./backend
    env_file: .env
    volumes:
      - workspace:/workspace
      - ./AGENTS.md:/workspace/AGENTS.md:ro
      - ./PRD.md:/workspace/PRD.md:ro
    depends_on:
      - redis
    restart: unless-stopped

  frontend:
    build: ./frontend
    depends_on:
      - backend
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - frontend
      - backend
    restart: unless-stopped

volumes:
  redis_data:
  workspace:
```

---

## 7. NON-GOALS (SENGAJA TIDAK DIKERJAKAN DI MVP)

1. **Multi-user / authentication** — single user, local deployment, tidak butuh auth
2. **Cloud deployment** — ini platform lokal di PC user
3. **Support model selain Claude** — tidak ada OpenAI/Gemini adapter di MVP
4. **Mobile responsive** — UI didesain untuk desktop browser
5. **Dark mode / theming** — satu tema saja di MVP
6. **Agent bisa modifikasi AGENTS.md atau PRD.md** — dokumen ini read-only untuk semua agent

---

## 8. CONSTRAINTS & ASUMSI

1. User punya koneksi internet (untuk Anthropic API)
2. Docker dan Docker Compose sudah terinstall di PC user
3. Untuk proyek firmware embedded: toolchain ARM (`arm-none-eabi-gcc`) sudah tersedia di dalam Docker image backend
4. User paham Bahasa Indonesia — semua komunikasi Lead Consultant ke user dalam Bahasa Indonesia
5. Anthropic API key tersedia dan sudah diaktifkan untuk model yang dipakai
6. Platform ini single-project-at-a-time untuk MVP

---

## 9. DELIVERY & ROLLOUT

### Phase 1 — Core Infrastructure (Priority 1)
- [ ] Docker Compose setup (redis, backend, frontend, nginx)
- [ ] Base `Agent` class dengan Anthropic API integration
- [ ] WebSocket event system (backend → frontend)
- [ ] Redis pub/sub event bus
- [ ] `project_state.json` schema + state manager

### Phase 2 — Agent Implementation (Priority 1)
- [ ] Lead Consultant agent (discovery, recommendation, escalation)
- [ ] Manager agent (task decomposition, routing, state tracking)
- [ ] Prompt Engineer agent
- [ ] Coder agent (single instance dulu)
- [ ] Reviewer agent
- [ ] Tester agent + subprocess sandbox execution
- [ ] Integrator agent

### Phase 3 — Frontend (Priority 1)
- [ ] Chat window Lead Consultant
- [ ] Agent status cards dengan animasi
- [ ] Escalation banner + response input
- [ ] Communication log panel

### Phase 4 — Polish MVP (Priority 2)
- [ ] React Flow node-graph visualization
- [ ] Team config panel (slider, toggle, model select)
- [ ] Multi-Coder support (spawn/terminate dynamic instances)
- [ ] Sandbox output streaming real-time ke UI
- [ ] Project management (create, switch, list)

---

## 10. OPEN QUESTIONS (perlu dijawab sebelum atau saat development)

| # | Pertanyaan | Owner | Status |
|---|---|---|---|
| 1 | Apakah Tester perlu support Docker-in-Docker untuk compile embedded firmware, atau cukup install toolchain langsung di backend image? | Wicaksu | Open |
| 2 | Apakah ada requirement minimum hardware lokal (RAM, CPU) untuk jalankan platform? | Wicaksu | Open |
| 3 | Apakah perlu session management (bisa pause platform, matikan Docker, nyalakan lagi dan lanjut)? | Wicaksu | Open |
| 4 | Berapa lama maksimal satu proyek boleh berjalan sebelum dianggap timeout? | Wicaksu | Open |

---

*PRD ini adalah dokumen hidup — bisa diupdate sesuai feedback setelah phase pertama selesai.*