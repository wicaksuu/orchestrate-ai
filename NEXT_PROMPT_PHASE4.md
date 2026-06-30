# NEXT PROMPT UNTUK AI KODING — PHASE 4 SIGMA QUALITY GATE

Phase 3 sudah terverifikasi untuk Docker hygiene, JSON body project creation, lifespan startup, cache cleanup, LLM provider abstraction, dan project state machine jalur utama.

Sekarang lanjutkan Phase 4: quality gate sebelum SIGMA dianggap MVP stabil untuk iterasi fitur.

## HASIL VERIFIKASI PHASE 3

Berhasil:

```bash
docker compose config
docker compose build
docker compose up -d
curl -s http://127.0.0.1/api/health
docker compose exec -T backend python -m pytest -o cache_dir=/tmp/pytest_cache
find backend -name '__pycache__' -o -name '*.pyc' -o -name '.pytest_cache'
```

Hasil:

- Backend tests: `9 passed`.
- Health check OK.
- Cache check kosong.
- Docker backend tidak lagi memakai `--reload`.
- Lifespan startup aktif.
- Project create JSON body bekerja.
- State machine jalur utama bekerja:
  - `init`
  - `discovery`
  - `team_recommended`
  - `running`
  - `completed`
- Logs/events/agent state memakai subject project `REST calculator API`.

Catatan:

- Ada beberapa command shell gabungan yang sempat gagal dengan `curl exit 7` saat stack baru direstart, tetapi endpoint sehat saat request dijalankan satuan. Buat test otomatis agar smoke test tidak bergantung pada timing manual.

## TASK WAJIB

### 1. Tambah integration tests untuk API state machine

Buat test FastAPI menggunakan `httpx.AsyncClient` atau test client yang sesuai lifespan.

Coverage wajib:

- Create project via JSON body.
- Create project via legacy query params.
- First non-approval message moves project `init -> discovery`.
- Direct approval on a fresh project does **not** start workflow and returns message asking for team recommendation.
- Recommendation message moves project to `team_recommended`.
- Approval after recommendation starts workflow and eventually project becomes `completed`.
- Logs contain recommendation, approval response, and workflow messages.
- Events endpoint returns event history.

Jangan rely pada `sleep 15` di test kalau bisa. Untuk workflow simulation, buat duration configurable via setting/env, misalnya:

```python
SIMULATION_STEP_DELAY_SECONDS: float = 2.0
```

Dalam test set ke `0.01`.

### 2. Tambah API untuk event history di frontend

Frontend saat ini sudah project-scoped untuk agents/logs, tetapi belum ada API client/store untuk `/api/events`.

Tambahkan:

- `SigmaEvent[]` state di Zustand.
- `api.getEvents(projectId, limit)`.
- `loadEvents()`.
- Load events saat project init/load.
- Handle WebSocket event dengan deduplication by `event_id`.

Jika UI belum menampilkan event history, tambahkan panel kecil atau tab pada log panel untuk event stream.

### 3. Perbaiki project state transition `approved`

Di Phase 3, approval menyimpan `approved` lalu langsung `running`, sehingga status `approved` hampir tidak bisa diamati.

Implementasi yang lebih jelas:

- Saat approval diterima: set `approved`.
- Publish project status event.
- Saat workflow coroutine mulai: set `running`.
- Saat workflow selesai: set `completed`.

Tambahkan `project_status` event:

```json
{
  "event_type": "project_status",
  "payload": {
    "project_id": "...",
    "status": "approved | running | completed"
  }
}
```

Frontend harus update active project status jika menerima event ini.

### 4. Perbaiki LLM provider config

Tambahkan ke `Settings`:

```python
LLM_PROVIDER: str = "simulated"
ANTHROPIC_API_KEY: str = ""
DEFAULT_MODEL: str = "claude-sonnet-4-6"
```

Ubah `get_llm_provider()` agar menerima settings atau membaca dari `config.settings`, bukan `os.getenv` langsung.

Tambahkan tests:

- default provider simulated.
- anthropic tanpa API key fallback simulated + warning.
- anthropic dengan API key membuat `AnthropicLLMProvider` tanpa mengekspos key di logs.

### 5. Jangan fallback diam-diam saat Anthropic API runtime error

`AnthropicLLMProvider.complete()` saat ini mengembalikan string fallback pada API error. Untuk production behavior, lebih baik:

- Raise custom `LLMProviderError`.
- Orchestrator yang menangkap error dan membuat user-facing response.
- Jangan masukkan detail API key atau raw sensitive error ke user response.

Tambahkan tests untuk sanitasi error.

### 6. Tambah frontend typecheck dalam verifikasi Docker

Docker build nginx sudah menjalankan `npm run build`, tetapi pastikan README mencantumkan:

```bash
docker compose build nginx
```

dan local:

```bash
cd frontend
npm install
npm run typecheck
npm run build
```

Jika memungkinkan tambahkan CI-style script root:

```bash
./tools/test_all.sh
```

yang menjalankan:

- docker compose config
- docker compose build
- docker compose up -d
- backend pytest
- health check
- smoke test state machine

### 7. Perbaiki docs status produk

README harus jelas bahwa:

- MVP masih simulated by default.
- Anthropic mode tersedia tapi belum diklaim production-ready tanpa valid API key test.
- Redis persistence dipakai.
- Single active running workflow masih asumsi utama.

## VERIFIKASI WAJIB

Jalankan:

```bash
docker compose config
docker compose build
docker compose up -d
curl -s http://127.0.0.1/api/health
docker compose exec -T backend python -m pytest -o cache_dir=/tmp/pytest_cache
find backend -name '__pycache__' -o -name '*.pyc' -o -name '.pytest_cache'
```

Smoke test:

```bash
P=$(curl -s -X POST http://127.0.0.1/api/project \
  -H 'Content-Type: application/json' \
  -d '{"name":"CalculatorAPI","description":"REST calculator API"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["project_id"])')

curl -s -X POST http://127.0.0.1/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P\",\"content\":\"Saya ingin membuat Calculator API\"}"

curl -s -X POST http://127.0.0.1/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P\",\"content\":\"rekomendasikan tim\"}"

curl -s -X POST http://127.0.0.1/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P\",\"content\":\"saya setuju, mulai\"}"

sleep 3

curl -s "http://127.0.0.1/api/project?project_id=$P"
curl -s "http://127.0.0.1/api/events?project_id=$P&limit=50"
curl -s "http://127.0.0.1/api/logs?project_id=$P"
curl -s "http://127.0.0.1/api/agents?project_id=$P"
```

Acceptance:

- Tests pass.
- Cache check returns empty.
- Direct approval without recommendation is blocked by test.
- Project emits observable `approved`, `running`, and `completed` status events.
- Frontend can load and store event history.
- README accurately describes current limitations.

## FORMAT LAPORAN

Laporkan:

```text
PHASE 4 SUMMARY
- Integration tests added
- Project status events
- Frontend event history support
- LLM provider config/error handling
- Docs/tooling updates
- Verification commands and results
- Remaining limitations
```
