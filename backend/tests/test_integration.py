import pytest
from httpx import AsyncClient, ASGITransport
from main import app
from config import settings

@pytest.mark.asyncio
async def test_project_lifecycle_integration():
    # Set delay simulasi sangat rendah untuk integrasi test
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
        
        # Tunggu workflow selesai (delay sangat rendah 0.01s * 6 langkah)
        import asyncio
        await asyncio.sleep(0.5)
        
        # 6. Pastikan status menjadi completed
        res_proj_completed = await ac.get(f"/api/project?project_id={proj_id}")
        assert res_proj_completed.json()["status"] == "completed"
        
        # 7. Pastikan log mengandung workflow messages
        logs_res = await ac.get(f"/api/logs?project_id={proj_id}")
        logs_data = logs_res.json()
        assert len(logs_data) > 0
        
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
