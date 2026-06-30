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
  if curl -s http://127.0.0.1/api/health > /dev/null; then
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
  local timeout="${3:-30}"
  echo "Menunggu status proyek menjadi '$expected'..."
  for idx in $(seq 1 "$timeout"); do
    status=$(curl -s "http://127.0.0.1/api/project?project_id=$project_id" | python3 -c 'import sys,json; print(json.load(sys.stdin)["status"])')
    if [ "$status" = "$expected" ]; then
      echo "Status berhasil berubah menjadi '$expected'!"
      return 0
    fi
    sleep 1
  done
  echo "ERROR: Batas waktu menunggu status '$expected' habis! Status saat ini: '$status'."
  return 1
}

echo "=== 5. Menjalankan Unit & Integration Tests ==="
docker compose exec -T backend python -m pytest -o cache_dir=/tmp/pytest_cache

echo "=== 6. Menjalankan Smoke Test Alur State Machine ==="
P=$(curl -s -X POST http://127.0.0.1/api/project \
  -H 'Content-Type: application/json' \
  -d '{"name":"SmokeAPI","description":"CI integration smoke test"}' \
  | python3 -c 'import sys,json; print(json.load(sys.stdin)["project_id"])')

echo "Project ID Baru: $P"

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

# Tunggu status beralih ke completed (workflow berjalan secara background)
wait_for_status "$P" "completed"

echo "=== 7. Verifikasi Kebersihan Cache Python ==="
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
