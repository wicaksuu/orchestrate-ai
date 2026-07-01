import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from config import settings
from core.db import database_manager
from core.orchestrator import orchestrator


async def wait_for_project_status(ac: AsyncClient, project_id: str, expected: str, timeout: float = 15.0):
    import asyncio
    import time

    deadline = time.monotonic() + timeout
    last_status = None
    while time.monotonic() < deadline:
        res = await ac.get(f"/api/project?project_id={project_id}")
        assert res.status_code == 200
        last_status = res.json()["status"]
        if last_status == expected:
            return
        await asyncio.sleep(0.1)
    raise AssertionError(f"Project status did not become {expected!r}; last status was {last_status!r}")


class FakeWorkflowProvider:
    """Provider palsu yang mensimulasikan output agent untuk testing."""
    def __init__(self):
        self._reviewer_call_count = 0

    async def complete(self, *, system_prompt, messages, model, max_tokens=4000):
        content = messages[-1]["content"].lower() if messages else ""
        system_lower = system_prompt.lower() if system_prompt else ""

        # Coder: generate file blocks
        if "generate the raw source code" in content or "tuliskan kode sumber" in content:
            return """Coder selesai.

# FILE: README.md
```markdown
# Test Project
```

# FILE: src/main.py
```python
def main():
    return "SIGMA test artifact"
```
"""
        # Coder revision fix
        if "reviewer has found issues" in content or "fix the issues" in content:
            return """Coder perbaikan selesai.

# FILE: src/main.py
```python
def main():
    return "SIGMA test artifact - fixed"
```
"""

        # Reviewer: first call returns REVISION_NEEDED, second returns APPROVED
        if "review the code" in content or "code reviewer" in system_lower:
            self._reviewer_call_count += 1
            if self._reviewer_call_count == 1:
                return "# REVISION_NEEDED\nBug ditemukan: fungsi main() perlu handling error."
            return "# APPROVED\nKode telah diperbaiki dan lolos review."

        # Tester: generate test files
        if "write unit tests" in content or "test plan" in content:
            return """Tester selesai.

# FILE: tests/test_main.py
```python
from src.main import main


def test_main():
    assert "SIGMA" in main()
```
"""
        return "Agent test response."

@pytest.mark.asyncio
async def test_project_lifecycle_integration(monkeypatch):
    # Test memakai provider palsu via monkeypatch agar CI tidak bergantung API eksternal.
    fake_provider = FakeWorkflowProvider()

    async def fake_get_agent_llm(project_id, agent_name):
        return fake_provider, "test-model"

    monkeypatch.setattr(orchestrator, "_get_agent_llm", fake_get_agent_llm)
    monkeypatch.setattr("core.orchestrator.get_llm_provider", lambda *args, **kwargs: fake_provider)
    monkeypatch.setattr(settings, "WORKSPACE_ROOT", "./sandbox_test_dir")
    settings.SIMULATION_STEP_DELAY_SECONDS = 0.01
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Buat project via JSON body
        res = await ac.post("/api/project", json={"name": "IntegrationProj", "description": "Test Desc"})
        assert res.status_code == 200
        proj_data = res.json()
        proj_id = proj_data["project_id"]
        assert proj_data["name"] == "IntegrationProj"
        assert proj_data["status"] == "init"
        
        # 2. Pesan pertama (non-approval) mengubah status ke discovery
        res_chat = await ac.post("/api/chat", json={
            "project_id": proj_id,
            "content": "Halo, saya butuh bantuan mengembangkan platform SIGMA"
        })
        assert res_chat.status_code == 200
        
        res_proj = await ac.get(f"/api/project?project_id={proj_id}")
        assert res_proj.status_code == 200
        assert res_proj.json()["status"] == "discovery"
        
        # 3. Kirim direct approval saat status discovery (tidak disetujui untuk jalan)
        res_chat_direct = await ac.post("/api/chat", json={
            "project_id": proj_id,
            "content": "setuju mulai"
        })
        assert res_chat_direct.status_code == 200
        # Harus mengembalikan pesan menyuruh rekomendasi tim
        messages = await ac.get(f"/api/logs?project_id={proj_id}")
        # Ambil pesan terakhir (yang dikirim Lead Consultant)
        last_lc_msg = messages.json()[-1]["content"]
        assert "belum menyusun rekomendasi tim" in last_lc_msg
        
        # 4. Minta rekomendasi tim
        res_rec = await ac.post("/api/chat", json={
            "project_id": proj_id,
            "content": "rekomendasikan tim"
        })
        assert res_rec.status_code == 200
        
        res_proj_rec = await ac.get(f"/api/project?project_id={proj_id}")
        assert res_proj_rec.json()["status"] == "team_recommended"
        
        # 5. Setuju mulai setelah rekomendasi
        res_approve = await ac.post("/api/chat", json={
            "project_id": proj_id,
            "content": "saya setuju, mulai"
        })
        assert res_approve.status_code == 200
        
        # Tunggu workflow real selesai tanpa bergantung fixed sleep.
        await wait_for_project_status(ac, proj_id, "completed")
        
        # 6. Pastikan status menjadi completed
        res_proj_completed = await ac.get(f"/api/project?project_id={proj_id}")
        assert res_proj_completed.json()["status"] == "completed"
        
        # 7. Pastikan log mengandung workflow messages
        logs_res = await ac.get(f"/api/logs?project_id={proj_id}")
        logs_data = logs_res.json()
        assert len(logs_data) > 0
        assert any("Platform Log: Agent ini berhasil membuat/memodifikasi file" in m["content"] for m in logs_data)
        
        # 8. Pastikan events endpoint bekerja dan urutan status proyek benar
        events_res = await ac.get(f"/api/events?project_id={proj_id}")
        assert events_res.status_code == 200
        events_data = events_res.json()
        assert len(events_data) > 0
        
        status_events = [
            e["payload"]["status"] for e in events_data
            if e["event_type"] == "project_status"
        ]
        
        # Urutan event minimal harus mengandung approved, running, lalu completed
        assert len(status_events) >= 3
        assert "approved" in status_events
        assert "running" in status_events
        assert "completed" in status_events
        
        # Cari index masing-masing status
        idx_approved = status_events.index("approved")
        idx_running = status_events.index("running")
        idx_completed = status_events.index("completed")
        
        assert idx_approved < idx_running < idx_completed

        # 9. Pastikan revision_loop events terjadi
        revision_events = [
            e for e in events_data
            if e["event_type"] == "revision_loop"
        ]
        # FakeWorkflowProvider mengembalikan REVISION_NEEDED pada call pertama,
        # lalu APPROVED pada call kedua. Harus ada minimal 2 revision events.
        assert len(revision_events) >= 2
        decisions = [e["payload"]["decision"] for e in revision_events]
        assert "REVISION_NEEDED" in decisions
        assert "APPROVED" in decisions


@pytest.mark.asyncio
async def test_agent_ai_settings_api_masks_api_key():
    database_manager.use_fallback = True
    database_manager._agent_ai_settings.clear()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        project_res = await ac.post(
            "/api/project",
            json={"name": "AIConfigProject", "description": "Agent AI settings test"},
        )
        assert project_res.status_code == 200
        project_id = project_res.json()["project_id"]

        save_res = await ac.post(
            f"/api/config/agent-ai?project_id={project_id}",
            json={
                "agent_name": "LeadConsultant",
                "provider": "openai",
                "model": "gpt-5.5",
                "api_key": "test-secret-token",
            },
        )
        assert save_res.status_code == 200
        saved = save_res.json()
        assert saved["api_key_configured"] is True
        assert "api_key" not in saved

        get_res = await ac.get(f"/api/config/agent-ai?project_id={project_id}")
        assert get_res.status_code == 200
        public_settings = get_res.json()
        assert public_settings == [
            {
                "agent_name": "LeadConsultant",
                "provider": "openai",
                "model": "gpt-5.5",
                "api_key_configured": True,
                "updated_at": public_settings[0]["updated_at"],
            }
        ]
        assert "test-secret-token" not in get_res.text

    database_manager._agent_ai_settings.clear()
