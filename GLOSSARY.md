# GLOSSARY.md — SIGMA Platform: Definisi Istilah

> Dokumen ini adalah referensi tunggal untuk semua istilah yang digunakan di platform SIGMA. Jika ada istilah yang ambigu dalam komunikasi antar agent, definisi di sini yang berlaku. Agent WAJIB menggunakan istilah sesuai definisi ini — jangan parafrase atau ganti dengan sinonim yang bisa menimbulkan ambiguitas.

---

## A

**AGENTS.md**
Dokumen konstitusi platform yang mendefinisikan semua role agent, aturan komunikasi, protocol, dan workspace structure. Read-only untuk semua agent. Konflik antara instruksi runtime dan AGENTS.md → AGENTS.md yang menang.

**Agent**
Satu instance LLM (Claude) dengan system prompt, history, dan role tertentu yang berjalan sebagai asyncio coroutine di dalam SIGMA backend. Satu agent = satu role = satu context window yang isolated.

**Agent Pool**
Kumpulan semua agent yang sedang aktif dalam satu project session. Komposisi direkomendasikan Lead Consultant, disetujui user, dieksekusi Manager.

**Approval**
Keputusan eksplisit dari user (melalui Lead Consultant) atau dari Reviewer/Tester (ke Manager) yang mengizinkan suatu task/output untuk lanjut ke tahap berikutnya. Tidak ada implicit approval — harus eksplisit.

**ARCHITECTURE.md**
Dokumen keputusan teknis yang sudah dilock: stack, pattern, dependency rules, failure handling. Agent tidak boleh re-decide hal yang sudah ada di sini.

---

## B

**BaseAgent**
Python class induk dari semua agent di SIGMA. Menyediakan: history management, status tracking, API call ke Anthropic, event publication. Semua role agent extends class ini.

**Blocking**
Kondisi di mana pipeline eksekusi berhenti menunggu input/keputusan dari luar agent. Ada dua jenis:
- `WAITING_REVIEW` — nunggu agent lain (Reviewer)
- `WAITING_USER_INPUT` — nunggu user, seluruh pipeline pause

**BLOCKER**
Kategori finding di review report Reviewer yang menandakan kode TIDAK BOLEH lanjut ke Tester sampai masalah ini diperbaiki. Contoh: logic error, overflow risk, missing error handling critical.

**Brief**
Dokumen instruksi teknis yang ditulis Prompt Engineer untuk Coder. Tersimpan di `tasks/{task_id}/brief.md`. Harus self-contained — Coder tidak perlu konteks lain selain brief ini untuk mulai bekerja.

**Broadcast**
Message yang dikirim ke semua agent aktif sekaligus. Digunakan Manager untuk pengumuman penting (misal: task cancelled, project scope change). Field `to` di message schema: `"BROADCAST"`.

---

## C

**CLAUDE.md / AGENTS.md**
Istilah yang sering dipakai bergantian di konteks platform Claude Code. Di SIGMA, dokumen yang setara adalah **AGENTS.md**.

**Coder**
Agent yang bertugas mengimplementasi kode berdasarkan brief dari Prompt Engineer. Bisa ada 1 sampai N instance (`CODER_1`, `CODER_2`, dst). Instance berbeda bisa mengerjakan modul berbeda secara paralel.

**CONVENTIONS.md**
Dokumen standar kode, naming, dan struktur yang WAJIB diikuti semua Coder. Reviewer berhak REJECT kode yang melanggar CONVENTIONS.md.

**Context Window**
Batas total token yang bisa diproses satu agent dalam satu session (history in + out). Setiap agent maintain history-nya sendiri untuk mencegah context window membengkak.

**Coroutine**
Unit eksekusi async Python (`async def`). Semua agent di SIGMA berjalan sebagai coroutine dalam satu asyncio event loop — bukan thread atau process terpisah.

---

## D

**Deliverable**
Output final yang dihasilkan Integrator setelah semua modul selesai, lolos review, dan lolos test. Tersimpan di `/workspace/deliverables/`. Ini yang dilaporkan Lead Consultant ke user sebagai hasil akhir project.

**Discovery**
Fase awal conversation Lead Consultant dengan user sebelum tim diaktifkan. Tujuan: memahami goal, scope, constraint, output yang diharapkan, dan timeline. Lead Consultant TIDAK BOLEH aktifkan tim sebelum discovery selesai.

**DONE**
Status terminal yang menandakan agent selesai dengan sub-task-nya dan output sudah dikirim ke Manager. DONE bukan "saya pikir sudah selesai" — harus ada output yang konkret.

**Dynamic Agent**
Agent yang bisa di-spawn atau di-terminate di tengah project (contoh: Coder tambahan). Hanya Manager yang boleh spawn/terminate agent, atas persetujuan user melalui Lead Consultant.

---

## E

**Escalation**
Mekanisme di mana agent (melalui Manager → Lead Consultant) membawa isu ke user karena tidak bisa diselesaikan di dalam tim. Trigger: deadlock antar agent, missing info, physical action required, repeated failure.

**Event**
Notifikasi real-time yang dipublish ke Redis Stream dan di-push ke frontend via WebSocket setiap kali ada perubahan state signifikan (status change, new message, escalation, compile output).

**Event Bus**
Sistem pub/sub berbasis Redis yang memungkinkan agent publish event tanpa perlu tahu siapa subscriber-nya. Decouples agent dari UI dan dari agent lain.

**Explicit Done**
Prinsip bahwa selesai harus dinyatakan secara eksplisit (kirim status `DONE` ke Manager), bukan diasumsikan selesai setelah tidak ada pesan lagi.

---

## F

**Failure Mode**
Kondisi error yang sudah diprediksi beserta cara penanganannya (lihat ARCHITECTURE.md section 8). Agent wajib mengikuti failure handling yang sudah didefinisikan, bukan improvise.

**Finding**
Satu item dalam review report Reviewer. Setiap finding punya: severity (BLOCKER/MAJOR/MINOR), file, line, deskripsi masalah, dan rekomendasi fix.

---

## G

**GLOSSARY.md**
Dokumen ini. Definisi otoritatif untuk semua istilah di SIGMA.

---

## H

**History**
Daftar message `[{"role": "user", "content": ...}, {"role": "assistant", "content": ...}, ...]` yang di-maintain oleh setiap agent secara individual. Dikirim ke Anthropic API di setiap call untuk menjaga konteks percakapan agent tersebut.

---

## I

**Instance**
Satu objek agent yang sedang berjalan. `CODER_1` dan `CODER_2` adalah dua instance berbeda dari role yang sama (Coder) dengan history dan context berbeda.

**Integrator**
Agent yang menggabungkan semua modul yang sudah lolos Tester menjadi satu deliverable kohesif. Integrator TIDAK mengubah logic internal modul — hanya interface dan glue code.

**Isolated Context**
Prinsip bahwa setiap agent hanya tahu apa yang relevan untuk tugasnya. Coder tidak perlu baca log Manager. Reviewer tidak perlu baca history Coder — cukup kode yang di-review.

---

## L

**Lead Consultant**
Satu-satunya agent yang berkomunikasi langsung dengan user dalam Bahasa Indonesia. Bertanggung jawab discovery, rekomendasi tim, escalation handling, dan laporan final. Tidak pernah eksekusi kode.

**MAJOR**
Kategori finding di review report yang harus diperbaiki Coder, tapi tidak block jika ada mitigasi yang jelas dan terdokumentasi.

**Manager**
Agent orchestrator yang memecah task, mendelegasikan ke agent lain, track progress, dan memutuskan alur eksekusi. Tidak menulis kode, tidak review kode.

**Message**
Unit komunikasi antar agent yang mengikuti schema di AGENTS.md section 4.1. Semua message tersimpan di Redis Stream sebagai append-only log.

**MINOR**
Kategori finding di review report yang merupakan saran, bukan requirement. Coder bisa pilih ikuti atau jelaskan alasan tidak.

**Model**
LLM yang digunakan agent untuk generate response. Bisa dikonfigurasi per-agent. Default: `claude-sonnet-4-6` untuk sebagian besar agent, `claude-haiku-4-5-20251001` untuk agent dengan tugas lebih sederhana (Integrator, Documenter).

---

## O

**Orchestrator**
Komponen Python di backend (bukan agent) yang mengelola lifecycle agent pool: spawn, route message, terminate, detect blocking condition. Manager adalah agent yang menggunakan Orchestrator, bukan Orchestrator itu sendiri.

---

## P

**Physical Action Request**
Permintaan dari Tester (via Manager → Lead Consultant) untuk user melakukan sesuatu secara fisik (colok USB, power on board, dll). Seluruh pipeline pause sampai user konfirmasi selesai.

**Pipeline**
Urutan eksekusi task dari Planner → Prompt Engineer → Coder → Reviewer → Tester → Integrator. Bisa ada loop balik (Reviewer reject → Coder revisi) tapi dibatasi `MAX_REVISION_LOOPS`.

**PRD.md**
Product Requirements Document. Definisi lengkap produk SIGMA: goals, fitur, arsitektur, stack, non-goals. Read-only untuk semua agent.

**Project**
Satu unit kerja yang punya workspace sendiri di SIGMA. Setiap project punya AGENTS.md, team config, message log, dan deliverables terpisah. MVP: satu project aktif pada satu waktu.

**project_state.json**
File JSON di workspace root yang berisi state lengkap project yang sedang berjalan: task list, status tiap task, agent assignment, progress. Ditulis Manager dan Integrator, dibaca semua agent. Disimpan di Redis (bukan file fisik untuk performa), tapi eksportable ke JSON.

**Prompt Engineer**
Agent yang menyusun brief/instruksi teknis untuk Coder. Bukan yang nulis kode — hanya yang memastikan Coder punya semua informasi yang dibutuhkan sebelum mulai.

---

## R

**Redis Stream**
Data structure Redis yang digunakan untuk message log dan event log. Append-only, persistent, bisa di-replay. Digunakan untuk: `sigma:messages:{project_id}` dan `sigma:events:{project_id}`.

**Retry**
Percobaan ulang oleh Manager saat Coder atau agent lain gagal, maksimum `MAX_REVISION_LOOPS` kali sebelum eskalasi.

**Review**
Proses Reviewer memeriksa output Coder. Menghasilkan review report (JSON) dengan verdict APPROVED atau REJECTED + daftar findings.

**Reviewer**
Agent yang melakukan code review terhadap output Coder. Tidak menulis atau memodifikasi kode secara langsung.

---

## S

**Sandbox**
Direktori `/workspace/sandbox/` yang digunakan Tester untuk eksekusi subprocess. Terisolasi dari direktori lain. Command yang bisa dijalankan dibatasi oleh whitelist di ARCHITECTURE.md.

**SIGMA**
Nama platform ini: *Supervised Intelligent Group of Multi-Agents*. Sistem multi-agent development platform yang sedang dibangun.

**Spawn**
Aksi Manager untuk membuat instance agent baru di tengah project (misalnya menambah `CODER_2`). Hanya bisa dilakukan atas persetujuan user melalui Lead Consultant.

**State Machine**
Model status agent yang terdiri dari: IDLE, THINKING, WORKING, WAITING_REVIEW, WAITING_USER_INPUT, BLOCKED, DONE, ERROR. Transisi antar status mengikuti aturan di AGENTS.md section 5.

**Sub-task**
Unit kerja terkecil yang bisa dikerjakan satu agent dalam satu session. Manager memecah task besar menjadi sub-task sebelum assign ke agent.

**System Prompt**
Instruksi permanen yang mendefinisikan role, tanggung jawab, dan aturan satu agent. Tersimpan di `backend/prompts/{role}.md`. Tidak berubah selama satu project session.

---

## T

**Task**
Unit kerja yang di-assign Manager ke satu atau lebih agent. Punya `task_id` (UUID), brief, status, dan history revisi.

**Team Config**
Konfigurasi komposisi tim aktif: agent apa saja yang aktif, berapa instance Coder, model mana yang dipakai tiap agent. Tersimpan di Redis, bisa diubah via UI dengan persetujuan user.

**Terminate**
Aksi Manager untuk mematikan instance agent yang tidak lagi dibutuhkan. History agent yang di-terminate di-archive ke Redis sebelum dihapus dari memori.

**Tester**
Agent yang menjalankan compile check dan unit test secara beneran via subprocess. Bukan hanya analisis — eksekusi nyata.

**Token**
Unit pengukuran input/output LLM. Setiap API call ke Anthropic dikenai biaya berdasarkan token. Agent wajib kirim konteks minimal yang relevan untuk efisiensi token.

**Toolchain**
Kumpulan tools kompilasi yang tersedia di sandbox. Untuk embedded firmware: `arm-none-eabi-gcc`. Untuk host testing: `gcc`. Sudah tersedia di Docker image backend.

**Trade-off Analysis**
Bagian wajib dari rekomendasi Lead Consultant ke user. Setiap rekomendasi harus disertai: kelebihan, kekurangan, estimasi token cost, dan risiko.

---

## U

**User**
Pemilik dan operator platform SIGMA. Satu-satunya yang boleh: approve komposisi tim, respond escalation, memberikan physical action confirmation, dan menyatakan project DONE.

---

## W

**WAITING_USER_INPUT**
Status blocking di mana seluruh pipeline pause karena ada keputusan atau aksi yang hanya bisa dilakukan user. Ditampilkan sebagai alert banner oranye di UI. Pipeline tidak lanjut sampai user respond.

**WebSocket**
Protokol komunikasi bidirectional antara SIGMA backend dan frontend browser. Digunakan untuk push semua event real-time (status update, new message, escalation, compile output) ke UI.

**Workspace**
Direktori kerja satu project di SIGMA (`/workspace/{project_id}/`). Berisi semua file task, deliverables, dan logs. Di-mount sebagai Docker volume agar persist.

**WORKSPACE_ROOT**
Environment variable yang mendefinisikan root direktori workspace. Default: `/workspace`. Semua path yang dipakai agent harus berada dalam `WORKSPACE_ROOT` — tidak ada akses ke luar direktori ini.

---

## Z

**Zustand**
State management library React yang digunakan frontend SIGMA. Satu store per domain (agent, chat, log, escalation, config, project).