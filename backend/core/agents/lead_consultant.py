import uuid
from core.agent import BaseAgent
from core.constants import AgentName, AgentStatus
from core.schemas import EscalationRequest
from core.state_manager import state_manager

class LeadConsultantAgent(BaseAgent):
    """Lead Consultant bertugas sebagai interface utama antara user dan tim agent."""
    def __init__(self):
        super().__init__(
            name=AgentName.LEAD_CONSULTANT,
            system_prompt="Kamu adalah Lead Consultant. Bantu user merancang tim agent dan proyek dalam Bahasa Indonesia."
        )

    async def process_message(self, project_id: str, sender: str, content: str) -> str:
        self.history.append({"role": "user", "content": f"{sender}: {content}"})
        await self.update_status(AgentStatus.THINKING, project_id=project_id)
        
        import asyncio
        await asyncio.sleep(1)
        await self.update_status(AgentStatus.WORKING, project_id=project_id)
        await asyncio.sleep(1)

        # Logika simulasi sederhana berdasarkan kata kunci
        content_lower = content.lower()
        if "halo" in content_lower or "hai" in content_lower:
            response = "Halo! Saya adalah Lead Consultant SIGMA. Proyek software atau firmware apa yang ingin Anda kembangkan hari ini? Saya bisa membantu mengoordinasikan tim AI agent untuk menyelesaikannya."
        elif "tim" in content_lower or "rekomendasi" in content_lower or "config" in content_lower:
            response = "Berdasarkan kebutuhan awal Anda, saya merekomendasikan tim yang terdiri dari: 1 Manager, 1 Coder, 1 Reviewer, dan 1 Tester. Silakan sesuaikan konfigurasi tim di panel samping jika ingin merubahnya. Apakah Anda setuju untuk memulai?"
        elif "setuju" in content_lower or "mulai" in content_lower or "jalan" in content_lower:
            response = "Baik, saya akan meminta Manager untuk memulai fase perencanaan dan eksekusi proyek. Saya akan terus mengabari Anda di sini."
            # Memicu orkestrator (bisa dipanggil dari controller/orchestrator)
        elif "eskalasi" in content_lower or "tanya" in content_lower:
            # Contoh memicu eskalasi
            esc_id = str(uuid.uuid4())
            esc = EscalationRequest(
                id=esc_id,
                project_id=project_id,
                agent_name=self.name,
                description="Apakah Anda ingin mengaktifkan opsi kompilasi ketat (strict compilation)?",
                options=["Ya, Aktifkan", "Tidak, Biarkan Default"],
                timeout_seconds=60
            )
            await state_manager.add_escalation(project_id, esc)
            response = f"Saya memerlukan konfirmasi Anda terkait konfigurasi build. Silakan klik opsi pada banner eskalasi di atas."
            await self.update_status(AgentStatus.WAITING_USER_INPUT, project_id=project_id)
            self.history.append({"role": "assistant", "content": response})
            return response
        else:
            response = f"Terima kasih atas masukannya. Saya telah mencatat: '{content}'. Saya akan meneruskannya ke tim pengembang untuk dianalisis lebih lanjut."

        self.history.append({"role": "assistant", "content": response})
        self.token_count += len(content.split()) + len(response.split())
        await self.update_status(AgentStatus.IDLE, response, project_id=project_id)
        return response
