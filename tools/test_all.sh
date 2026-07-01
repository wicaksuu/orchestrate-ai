#!/bin/bash
set -e

echo "=== 1. Validasi Docker Compose Config ==="
docker compose config > /dev/null

echo "=== 2. Membangun Container (Build) ==="
docker compose build

echo "=== 3. Menjalankan Container (Up) ==="
docker compose up -d

echo "=== 4. Menunggu Startup Backend ==="
for i in {1..10}; do
  if curl -sf http://127.0.0.1/api/health > /dev/null; then
    echo "Backend telah siap!"
    break
  fi
  echo "Menunggu backend (percobaan $i/10)..."
  sleep 2
done

# Helper function untuk menunggu status proyek tertentu (polling)
wait_for_status() {
  local project_id="$1"
  local expected="$2"
  local timeout="${3:-300}"
  echo "Menunggu status proyek menjadi '$expected' (timeout $timeout s)..."
  for idx in $(seq 1 "$timeout"); do
    status=$(curl -s "http://127.0.0.1/api/project?project_id=$project_id" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])' 2>/dev/null || echo "error")
    if [ "$status" = "$expected" ]; then
      echo "Status berhasil berubah menjadi '$expected'!"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: Batas waktu menunggu status '$expected' habis! Status saat ini: '$status'."
  return 1
}

create_project() {
  local name="$1"
  local description="$2"
  local response=""
  for idx in $(seq 1 10); do
    response=$(curl -sf -X POST http://127.0.0.1/api/project \
      -H 'Content-Type: application/json' \
      -d "{\"name\":\"$name\",\"description\":\"$description\"}" || true)
    if project_id=$(echo "$response" | python3 -c 'import sys,json; print(json.load(sys.stdin)["project_id"])' 2>/dev/null); then
      echo "$project_id"
      return 0
    fi
    echo "Menunggu endpoint project siap (percobaan $idx/10)..."
    sleep 1
  done
  echo "ERROR: Gagal membuat project. Response terakhir:"
  echo "$response"
  return 1
}

echo "=== 5. Menjalankan Unit & Integration Tests ==="
docker compose exec -T backend python -m pytest -o cache_dir=/tmp/pytest_cache

echo "=== 6. Menjalankan Smoke Test Alur State Machine ==="
P=$(create_project "SmokeAPI" "CI integration smoke test")

echo "Project ID Baru: $P"

echo "=== 7. Smoke Test Konfigurasi AI Agent ==="
AI_PROVIDER="${LLM_PROVIDER:-gemini}"
AI_MODEL="${DEFAULT_MODEL:-gemini-flash-latest}"
if [ "$AI_PROVIDER" = "openai" ] || [ "$AI_PROVIDER" = "codex" ]; then
  AI_MODEL="${OPENAI_MODEL:-gpt-5.5}"
fi

for AGENT in LeadConsultant Manager PromptEngineer Coder Reviewer Tester Integrator; do
  curl -s -X POST "http://127.0.0.1/api/config/agent-ai?project_id=$P" \
    -H 'Content-Type: application/json' \
    -d "{\"agent_name\":\"$AGENT\",\"provider\":\"$AI_PROVIDER\",\"model\":\"$AI_MODEL\"}" > /dev/null
done

AI_CONFIG=$(curl -s "http://127.0.0.1/api/config/agent-ai?project_id=$P")

echo "$AI_CONFIG" | python3 -c 'import sys,json; data=json.load(sys.stdin); assert len(data) == 7; assert all(item["provider"] != "simulated" for item in data); assert all("api_key" not in item for item in data)'

AI_CONFIG_PUBLIC=$(curl -s "http://127.0.0.1/api/config/agent-ai?project_id=$P")
echo "$AI_CONFIG_PUBLIC" | python3 -c 'import sys,json; data=json.load(sys.stdin); assert len(data) == 7; assert all(item["provider"] != "simulated" for item in data); assert all("api_key" not in item for item in data)'
if echo "$AI_CONFIG_PUBLIC" | grep -q "dummy-smoke-token"; then
  echo "ERROR: API token mentah bocor pada response publik."
  exit 1
fi

# Kirim pesan awal
curl -s -X POST http://127.0.0.1/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P\",\"content\":\"Saya ingin membuat CI Smoke API\"}" > /dev/null

# Tunggu status beralih ke discovery
wait_for_status "$P" "discovery"

# Minta rekomendasi tim
curl -s -X POST http://127.0.0.1/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P\",\"content\":\"rekomendasikan tim\"}" > /dev/null

# Tunggu status beralih ke team_recommended
wait_for_status "$P" "team_recommended"

# Setujui untuk jalan
curl -s -X POST http://127.0.0.1/api/chat \
  -H 'Content-Type: application/json' \
  -d "{\"project_id\":\"$P\",\"content\":\"saya setuju, mulai\"}" > /dev/null

# Tunggu status beralih ke completed (workflow LLM berjalan secara background, butuh waktu lebih lama)
wait_for_status "$P" "completed" 180

FILES_JSON=$(curl -s "http://127.0.0.1/api/project/files?project_id=$P")
echo "$FILES_JSON" | python3 -c 'import sys,json; data=json.load(sys.stdin); paths={item["path"] for item in data if not item["is_dir"]}; assert len(paths) > 0, "LLM seharusnya menghasilkan minimal 1 file di workspace"'

echo "=== 8. Verifikasi Kebersihan Cache Python ==="
CACHE_FILES=$(find backend -name '__pycache__' -o -name '*.pyc' -o -name '.pytest_cache')
if [ -n "$CACHE_FILES" ]; then
  echo "WARNING: Terdapat sisa cache di workspace:"
  echo "$CACHE_FILES"
  find backend -name "__pycache__" -exec rm -rf {} + || true
  rm -rf backend/.pytest_cache || true
else
  echo "Workspace bersih dari cache bytecode!"
fi

echo "=== VERIFIKASI BERHASIL 100% ==="
