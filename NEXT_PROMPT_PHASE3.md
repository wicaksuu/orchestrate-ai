# NEXT PROMPT UNTUK AI KODING — PHASE 3 PRODUCTIZATION SIGMA

Phase 2 sudah terverifikasi untuk bugfix utama, event history, project-scoped agent status, dan project-aware simulation. Sekarang lanjutkan Phase 3: productization ringan tanpa rewrite total.

Tujuan fase ini: mengurangi demo-only behavior, membersihkan developer hygiene, dan menyiapkan jalur integrasi LLM sungguhan.

## HASIL VERIFIKASI PHASE 2

Command yang berhasil:

```bash
docker compose config
docker compose build
docker compose up -d
curl -s http://localhost/api/health
docker compose exec -T backend python -m pytest
```

Hasil:

```text
9 passed in 0.09s
```

Smoke test manual:

- Project `CalculatorAPI` dengan deskripsi `REST calculator API` menghasilkan logs dan agent status berisi `REST calculator API`.
- Project kedua `InventoryApp` dengan deskripsi `Warehouse inventory tool` menghasilkan logs dan agent status berisi `Warehouse inventory tool`.
- Query berikut sudah terverifikasi:

```text
GET /api/logs?project_id=<id>
GET /api/agents?project_id=<id>
GET /api/events?project_id=<id>&limit=20
```

- Project-scoped status tidak saling menimpa: project Calculator tetap menampilkan `REST calculator API`, project Inventory menampilkan `Warehouse inventory tool`.
- Backend logs tidak menunjukkan traceback.

## CATATAN YANG MASIH PERLU DIBERESKAN

### 1. Cache Python masih muncul di workspace

Walaupun `.gitignore` sudah benar, file berikut masih muncul di source tree setelah test/server:

```text
backend/**/__pycache__/
backend/.pytest_cache/
```

Penyebab utama:

- `backend` di-bind mount ke `/app`.
- Uvicorn dijalankan dengan `--reload`.
- Python menulis bytecode ke source tree.
- Belum terlihat ada `.dockerignore`, jadi cache berisiko ikut build context.

Perbaikan:

- Tambahkan `backend/.dockerignore` dan `frontend/.dockerignore`.
- Tambahkan environment di Docker backend:

```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
```

- Untuk Docker compose default, pertimbangkan hapus `--reload` dari `CMD` backend agar container default lebih mirip production. Jika tetap ingin dev reload, buat profile/override terpisah atau dokumentasikan.
- Bersihkan cache existing dari workspace.
- Pastikan `rg --files -g '*__pycache__*' -g '*.pyc' -g '.pytest_cache'` tidak mengembalikan file setelah test.

### 2. API project creation masih memakai query params

Saat ini create project memakai:

```text
POST /api/project?name=...&description=...
```

Untuk API yang lebih bersih, tambahkan request body schema:

```json
{
  "name": "CalculatorAPI",
  "description": "REST calculator API"
}
```

Requirement:

- Tetap backward compatible dengan query params jika frontend masih memakai format lama.
- Frontend `api.createProject()` harus dipindah ke JSON body.
- Tambahkan test endpoint untuk body request.

### 3. UI harus benar-benar memakai project-scoped endpoint

Pastikan frontend memakai:

```text
GET /api/agents?project_id=<active_project_id>
GET /api/events?project_id=<active_project_id>
```

Requirement:

- `loadAgents()` di Zustand store harus menggunakan active `project.project_id`.
- WebSocket sudah project-scoped, pertahankan.
- Tambahkan UI call untuk event history jika panel log/event membutuhkan initial replay.
- Saat switching project, state agents/logs/events harus reload dari project yang dipilih, bukan state global.

### 4. Tambahkan LLM provider abstraction

Jangan langsung sebar Anthropic SDK di tiap agent. Buat abstraction:

```text
backend/core/llm/
├── __init__.py
├── base.py
├── simulated.py
└── anthropic_provider.py
```

Interface minimal:

```python
class LLMProvider(Protocol):
    async def complete(
        self,
        *,
        system_prompt: str,
        messages: list[dict[str, str]],
        model: str,
        max_tokens: int,
    ) -> str: ...
```

Implementasi:

- `SimulatedLLMProvider`: default untuk development/test.
- `AnthropicLLMProvider`: aktif jika `LLM_PROVIDER=anthropic` dan `ANTHROPIC_API_KEY` tersedia.

Requirement:

- Jangan log API key.
- Jika provider anthropic dipilih tapi API key kosong, fail loudly saat startup atau fallback eksplisit dengan warning yang jelas, pilih salah satu dan dokumentasikan.
- Agent tetap bisa berjalan dengan simulation tanpa network.
- Tambahkan tests untuk provider selection.

### 5. Lead Consultant discovery flow belum mengikuti konstitusi

Saat ini `setuju mulai` langsung memicu workflow. Untuk demo boleh, tapi untuk MVP SIGMA perlu state discovery minimal.

Tambahkan project phase sederhana:

```text
init -> discovery -> team_recommended -> approved -> running -> completed
```

Minimal behavior:

- Pesan awal non-approval masuk ke `discovery`.
- Lead Consultant menanyakan/merangkum goal.
- Jika user meminta rekomendasi tim, response mencantumkan komposisi tim dan menunggu approval.
- Workflow hanya jalan jika project status `approved` atau jika pesan approval valid setelah recommendation.
- Setelah workflow selesai, status project menjadi `completed`.

Tambahkan tests:

- `setuju mulai` pada project baru tanpa rekomendasi tidak langsung menjalankan workflow, kecuali ada explicit dev/demo override.
- Setelah recommendation lalu approval, workflow berjalan.

Jika ini terlalu besar, buat sebagai minimal state machine dulu dan dokumentasikan limitation.

### 6. Frontend verification

Tambahkan script:

```json
{
  "scripts": {
    "typecheck": "tsc --noEmit"
  }
}
```

Pastikan verifikasi frontend jelas:

```bash
docker compose build nginx
cd frontend && npm install && npm run typecheck && npm run build
```

Jika local `node_modules` tidak ingin dibuat, cukup gunakan Docker build untuk CI-like build, tapi README harus jelas.

### 7. Modernize FastAPI startup

FastAPI `@app.on_event("startup")` masih bekerja, tapi path modern adalah lifespan.

Refactor ke:

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await state_manager.connect()
    await event_bus.connect()
    yield
    await state_manager.disconnect()
    await event_bus.disconnect()

app = FastAPI(..., lifespan=lifespan)
```

Tambahkan smoke test health agar startup tetap berjalan.

## VERIFIKASI WAJIB

Jalankan:

```bash
docker compose config
docker compose build
docker compose up -d
curl -s http://localhost/api/health
docker compose exec -T backend python -m pytest
```

Smoke test:

```bash
P1=$(curl -s -X POST http://localhost/api/project \
  -H 'Content-Type: application/json' \
  -d '{"name":"CalculatorAPI","description":"REST calculator API"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["project_id"])')

curl -s -X POST http://localhost/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P1\",\"content\":\"Saya ingin membuat Calculator API\"}"

curl -s -X POST http://localhost/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P1\",\"content\":\"rekomendasikan tim\"}"

curl -s -X POST http://localhost/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P1\",\"content\":\"saya setuju, mulai\"}"

sleep 15

curl -s "http://localhost/api/project?project_id=$P1"
curl -s "http://localhost/api/agents?project_id=$P1"
curl -s "http://localhost/api/events?project_id=$P1&limit=20"
curl -s "http://localhost/api/logs?project_id=$P1"
```

Cache check:

```bash
find backend -name '__pycache__' -o -name '*.pyc' -o -name '.pytest_cache'
```

Acceptance:

- Backend tests pass.
- No Pydantic/FastAPI deprecation warnings in tests/startup logs.
- Project create works with JSON body and old query param format.
- Frontend uses project-scoped agent endpoint.
- Event history endpoint still works.
- Project status reaches `completed` after approved workflow.
- Cache check returns empty after tests/server run.
- README contains accurate commands.

## FORMAT LAPORAN

Laporkan:

```text
PHASE 3 SUMMARY
- Hygiene fixes
- API changes
- LLM provider abstraction status
- Discovery/project phase state machine status
- Tests added/updated
- Verification commands and results
- Remaining limitations
```

Jangan klaim Anthropic integration production-ready kalau belum dites dengan `LLM_PROVIDER=anthropic` dan API key valid.
