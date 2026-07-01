# SIGMA — Supervised Intelligent Group of Multi-Agents

SIGMA adalah platform orkestasi multi-agent berbasis LLM untuk pengembangan perangkat lunak dan firmware.

## Fitur Utama

- **Lead Consultant Chat Interface**: Antarmuka obrolan natural berbasis Bahasa Indonesia.
- **Agent Visual Dashboard**: Menampilkan status real-time dari setiap sub-agent pengembang.
- **Communication Log**: Log komprehensif alur komunikasi antar agent.
- **Team Configuration**: Manajemen komposisi tim pengembang dan model LLM.
- **Per-Agent AI Provider Settings**: Setiap agent dapat memakai provider/model berbeda melalui UI, dengan token API tersimpan terenkripsi di MariaDB.
- **Sandbox Execution Environment**: Menjalankan pengujian program yang aman di dalam sandbox ber-whitelist.

## Cara Menjalankan

Langkah mudah untuk memulai seluruh platform menggunakan Docker Compose:

1. Pastikan Docker dan Docker Compose telah terinstal di sistem Anda.
2. Clone repositori ini dan masuk ke dalam folder proyek.
3. Jalankan perintah berikut:
   ```bash
   docker compose up --build
   ```
4. Buka browser Anda dan akses:
   ```text
   http://localhost
   ```

## Status MVP & Limitasi

- **Real Provider Only:** Runtime platform tidak memakai provider simulasi. Pastikan salah satu provider real dikonfigurasi di `.env` atau panel konfigurasi agent.
- **Google Gemini Integration:** Default runtime menggunakan Gemini. Konfigurasi minimal:
  ```env
  LLM_PROVIDER=gemini
  GEMINI_API_KEY=your_gemini_api_key_here
  DEFAULT_MODEL=gemini-flash-latest
  ```
- **Anthropic Claude Integration:** Anda dapat mengaktifkan integrasi Claude asli dengan menyetel variabel berikut pada berkas `.env`:
  ```env
  LLM_PROVIDER=anthropic
  ANTHROPIC_API_KEY=your_api_key_here
  ```
- **OpenAI/Codex Integration:** Jika Anda memiliki API key OpenAI/Codex, gunakan provider OpenAI melalui Responses API:
  ```env
  LLM_PROVIDER=openai
  OPENAI_API_KEY=your_openai_api_key_here
  OPENAI_MODEL=gpt-5.5
  ```
  Alias `LLM_PROVIDER=codex` juga didukung dan akan memakai provider OpenAI yang sama. Jangan pernah menaruh API key di chat atau commit; simpan hanya di `.env`.
- **Konfigurasi AI via UI:** Selain konfigurasi global `.env`, panel **Konfigurasi Tim** menyediakan setting provider/model/token per agent untuk setiap project. Token yang dikirim dari UI disimpan terenkripsi dan API publik hanya mengembalikan flag `api_key_configured`.
- **MariaDB Persistence:** Docker Compose menjalankan service `mariadb` untuk menyimpan konfigurasi AI per agent. Pastikan `SECRET_KEY` di `.env` diganti dari nilai default sebelum dipakai serius, karena key ini digunakan untuk enkripsi token.
- **Redis Persistence:** Redis digunakan sebagai message broker/event bus dan penyimpan status persistence log.
- **Single Active Workflow & Chat Concurrency Limitation:** Platform berasumsi hanya ada satu workflow aktif yang berjalan secara paralel untuk masing-masing project ID pada satu waktu. Endpoint `/api/chat` memproses pesan secara asinkron (fire-and-forget). Oleh karena itu, pemanggil (caller) disarankan untuk tidak mengirim pesan berturut-turut tanpa menunggu respons status/event sebelumnya (misalnya via polling status project atau memantau WebSocket stream) guna menghindari race condition status proyek.

## Menjalankan Pengujian

### 1. Script Verifikasi Otomatis (CI-Style)
Kami menyediakan script orkestrasi pengujian otomatis yang akan melakukan build, pengujian unit, pengujian integrasi, hingga smoke test alur state machine:

```bash
chmod +x tools/test_all.sh
./tools/test_all.sh
```

### 2. Pengujian Manual
Untuk menjalankan unit test backend di dalam container:

```bash
docker compose exec -T backend python -m pytest -o cache_dir=/tmp/pytest_cache
```

Untuk melakukan build frontend secara manual di Docker:

```bash
docker compose build nginx
```

Untuk melakukan typecheck dan build lokal:

```bash
cd frontend
npm install
npm run typecheck
npm run build
```
