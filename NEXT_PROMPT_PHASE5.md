# NEXT PROMPT UNTUK AI KODING — PHASE 5 FRONTEND REALTIME & RACE HARDENING

Phase 4 backend quality gate sudah pass, tetapi review manual menemukan satu gap frontend realtime yang belum tertangkap test.

## HASIL VERIFIKASI PHASE 4

Berhasil:

```bash
sh tools/test_all.sh
```

Hasil:

- Docker compose config/build/up sukses.
- Backend pytest: `10 passed`.
- Smoke test state machine mencapai `completed`.
- Cache check bersih.
- Backend event history memuat `project_status` events: `approved`, `running`, `completed`.

## BUG WAJIB DIPERBAIKI

### 1. WebSocket tidak memanggil `handleNewEvent`

`frontend/src/store/sigmaStore.ts` sudah punya:

```ts
events: SigmaEvent[]
loadEvents()
handleNewEvent(event)
```

`handleNewEvent()` juga sudah bisa update `project.status` saat menerima event:

```ts
event.event_type === "project_status"
```

Tetapi `frontend/src/hooks/useWebSocket.ts` belum mengambil `handleNewEvent` dari store dan belum memanggilnya untuk setiap event. Akibatnya:

- Event realtime tidak masuk ke `events`.
- `project_status` realtime tidak mengubah active project status di frontend.
- Store hanya benar kalau `loadEvents()` dipanggil ulang manual.

Perbaikan:

- Destructure `handleNewEvent` dari `useSigmaStore()`.
- Pada `socket.onmessage`, panggil `handleNewEvent(sigmaEvent)` untuk semua event valid sebelum/atau setelah switch khusus.
- Pastikan deduplication tetap di store, bukan di hook.

Contoh:

```ts
const {
  handleAgentStatusUpdate,
  handleNewMessage,
  handleNewEscalation,
  handleEscalationResolved,
  handleNewEvent,
  loadAgents,
} = useSigmaStore()

socket.onmessage = (event) => {
  const sigmaEvent: SigmaEvent = JSON.parse(event.data)
  handleNewEvent(sigmaEvent)
  ...
}
```

### 2. Tambahkan frontend unit test ringan untuk store event handling

Tambahkan test minimal untuk Zustand store jika memungkinkan.

Coverage:

- Given active project status `approved`.
- When `handleNewEvent({ event_type: "project_status", payload: { status: "running" } })`.
- Then `project.status === "running"`.
- Duplicate event id tidak menambah event kedua kali.

Jika belum ada test runner frontend, tambahkan Vitest secara minimal atau dokumentasikan alasan belum menambah dependency. Jika menambah Vitest:

```bash
npm install -D vitest
```

dan scripts:

```json
"test": "vitest run"
```

### 3. Perbaiki `tools/test_all.sh` agar tidak race antar chat messages

Script smoke test Phase 4 mengirim tiga chat message berurutan tanpa menunggu respons background:

```bash
POST first message
POST rekomendasikan tim
POST saya setuju, mulai
```

Karena `/api/chat` hanya mengembalikan `processing`, urutan background task bisa race. Dalam log verifikasi, workflow tetap selesai, tetapi response discovery/recommendation bisa muncul setelah approval.

Perbaikan:

- Tambahkan helper polling di script untuk menunggu project status tertentu.
- Setelah pesan pertama, tunggu status `discovery`.
- Setelah rekomendasi, tunggu status `team_recommended`.
- Setelah approval, tunggu status `completed`.

Contoh fungsi:

```bash
wait_for_status() {
  local project_id="$1"
  local expected="$2"
  local timeout="${3:-30}"
  for i in $(seq 1 "$timeout"); do
    status=$(curl -s "http://127.0.0.1/api/project?project_id=$project_id" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
    if [ "$status" = "$expected" ]; then
      return 0
    fi
    sleep 1
  done
  echo "ERROR: timed out waiting for $expected, got $status"
  return 1
}
```

Use `127.0.0.1` consistently instead of `localhost`.

### 4. Tambahkan backend integration assertion untuk `project_status` events

`test_integration.py` harus memverifikasi events endpoint mengandung:

```text
project_status approved
project_status running
project_status completed
```

Urutan harus benar.

### 5. Dokumentasikan remaining limitation concurrency

README perlu mencatat bahwa `/api/chat` saat ini asynchronous fire-and-forget dan caller sebaiknya menunggu status/event, bukan mengirim banyak stateful command tanpa polling.

## VERIFIKASI WAJIB

Jalankan:

```bash
sh tools/test_all.sh
```

Jika menambah frontend tests:

```bash
cd frontend
npm run typecheck
npm run test
npm run build
```

Acceptance:

- `tools/test_all.sh` pass.
- Backend integration test memverifikasi urutan `project_status` events.
- WebSocket hook memanggil `handleNewEvent`.
- Store test membuktikan `project_status` realtime mengubah `project.status`.
- Smoke test script tidak mengirim command stateful tanpa menunggu status antar langkah.

## FORMAT LAPORAN

Laporkan:

```text
PHASE 5 SUMMARY
- WebSocket event handling fix
- Frontend store tests
- Smoke script race hardening
- Backend integration assertions
- Verification results
- Remaining limitations
```
