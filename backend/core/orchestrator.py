import asyncio
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from core.constants import AgentName, AgentStatus, MessageType, MessagePriority
from core.schemas import SigmaEvent, AgentMessage, MessageMetadata, ProjectState
from core.event_bus import event_bus
from core.state_manager import state_manager
from core.llm import get_llm_provider
from core.llm.exceptions import LLMProviderError
from config import settings

# Import agents
from core.agents.lead_consultant import LeadConsultantAgent
from core.agents.manager import ManagerAgent
from core.agents.prompt_engineer import PromptEngineerAgent
from core.agents.coder import CoderAgent
from core.agents.reviewer import ReviewerAgent
from core.agents.tester import TesterAgent
from core.agents.integrator import IntegratorAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    """Orchestrator mengelola siklus hidup eksekusi multi-agent dan orkestrasinya."""
    def __init__(self):
        self.agents = {
            AgentName.LEAD_CONSULTANT: LeadConsultantAgent(),
            AgentName.MANAGER: ManagerAgent(),
            AgentName.PROMPT_ENGINEER: PromptEngineerAgent(),
            AgentName.CODER: CoderAgent(),
            AgentName.REVIEWER: ReviewerAgent(),
            AgentName.TESTER: TesterAgent(),
            AgentName.INTEGRATOR: IntegratorAgent(),
        }
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.llm = get_llm_provider()

    async def initialize_project(self, project_id: str):
        """Menginisialisasi status awal seluruh agent untuk proyek baru."""
        for name, agent in self.agents.items():
            state = await state_manager.get_agent_state(name.value, project_id)
            state.status = AgentStatus.IDLE
            state.last_message = f"Agent {name.value} siap digunakan."
            state.token_count = 0
            await state_manager.save_agent_state(state, project_id)

    async def handle_user_message(self, project_id: str, content: str):
        """Menangani pesan dari user ke Lead Consultant dengan Discovery Flow State Machine."""
        # 1. Dapatkan project state saat ini
        project_state = await state_manager.get_project_state(project_id)
        if not project_state:
            project_state = ProjectState(
                project_id=project_id,
                name="Project Default",
                status="init"
            )

        # Transisi Status Project: init -> discovery
        if project_state.status == "init":
            project_state.status = "discovery"
            await state_manager.save_project_state(project_state)
            logger.info(f"Project {project_id} beralih status menjadi 'discovery'")

        # 2. Simpan pesan user
        user_msg = AgentMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            message_type=MessageType.USER,
            content=content,
            priority=MessagePriority.MEDIUM,
            metadata=MessageMetadata(
                sender="User",
                receiver=AgentName.LEAD_CONSULTANT.value,
            )
        )
        await state_manager.append_message(project_id, user_msg)
        
        # Publish event message baru ke UI
        await event_bus.publish(
            project_id, 
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="message",
                payload=user_msg.model_dump()
            )
        )

        # 3. Proses di LeadConsultant menggunakan LLM Provider Abstraction
        lc_agent = self.agents[AgentName.LEAD_CONSULTANT]
        
        # Publish status LeadConsultant THINKING
        await lc_agent.update_status(AgentStatus.THINKING, project_id=project_id)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="agent_status",
                payload=(await lc_agent.get_state(project_id)).model_dump()
            )
        )

        content_lower = content.lower()
        response_content = ""

        # Deteksi transisi status ke team_recommended
        if "rekomendasi" in content_lower or "tim" in content_lower or "config" in content_lower:
            project_state.status = "team_recommended"
            await state_manager.save_project_state(project_state)
            logger.info(f"Project {project_id} beralih status menjadi 'team_recommended'")

        # Cek apakah user memberikan approval ("setuju" atau "mulai")
        is_approval = "setuju" in content_lower or "mulai" in content_lower

        if is_approval:
            if project_state.status != "team_recommended":
                response_content = "Mohon maaf, saya belum menyusun rekomendasi tim untuk proyek Anda. Silakan minta rekomendasi tim terlebih dahulu dengan mengetik 'rekomendasikan tim'."
            else:
                # Transisi approved
                project_state.status = "approved"
                await state_manager.save_project_state(project_state)
                logger.info(f"Project {project_id} beralih status menjadi 'approved'")
                
                # Pancarkan event project_status approved
                await event_bus.publish(
                    project_id,
                    SigmaEvent(
                        event_id=str(uuid.uuid4()),
                        project_id=project_id,
                        event_type="project_status",
                        payload={"project_id": project_id, "status": "approved"}
                    )
                )
                
                # Jalankan simulated workflow secara background
                if project_id not in self.running_tasks or self.running_tasks[project_id].done():
                    self.running_tasks[project_id] = asyncio.create_task(
                        self.run_simulated_workflow(project_id)
                    )
                response_content = "Persetujuan diterima. Saya telah meminta Manager untuk memulai fase perencanaan dan eksekusi proyek."
        else:
            # Panggil LLM provider complete() untuk menghasilkan response LeadConsultant
            history_msgs = await state_manager.get_messages(project_id)
            llm_messages = []
            for msg in history_msgs[-10:]:  # batasi history
                role = "user" if msg.message_type == MessageType.USER else "assistant"
                llm_messages.append({"role": role, "content": msg.content})

            try:
                response_content = await self.llm.complete(
                    system_prompt=lc_agent.system_prompt,
                    messages=llm_messages,
                    model=(
                        settings.OPENAI_MODEL
                        if settings.LLM_PROVIDER.lower() in {"openai", "codex"}
                        else settings.DEFAULT_MODEL
                    )
                )
            except LLMProviderError as lpe:
                logger.error(f"LLMProviderError terjadi: {lpe}")
                response_content = "Maaf, saya mengalami kendala teknis internal pada LLM provider. Permintaan Anda tetap dicatat namun saya belum bisa merespons lebih lanjut saat ini."
            except Exception as e:
                logger.error(f"Error pada LLM call: {e}")
                response_content = "Maaf, saya mengalami gangguan koneksi sementara. Silakan coba kembali sesaat lagi."

        # Simpan respons LeadConsultant
        lc_msg = AgentMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            message_type=MessageType.AGENT_COMM,
            content=response_content,
            priority=MessagePriority.MEDIUM,
            metadata=MessageMetadata(
                sender=AgentName.LEAD_CONSULTANT.value,
                receiver="User",
            )
        )
        await state_manager.append_message(project_id, lc_msg)
        
        # Publish status LeadConsultant IDLE
        await lc_agent.update_status(AgentStatus.IDLE, response_content, project_id=project_id)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="agent_status",
                payload=(await lc_agent.get_state(project_id)).model_dump()
            )
        )

        # Publish event message baru
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="message",
                payload=lc_msg.model_dump()
            )
        )

    async def run_simulated_workflow(self, project_id: str):
        """Mensimulasikan alur kerja pengembangan lengkap yang dinamis per project."""
        logger.info(f"Memulai alur simulasi orkestrasi untuk project {project_id}")
        
        # Transisi ke running
        project_state = await state_manager.get_project_state(project_id)
        if project_state:
            project_state.status = "running"
            await state_manager.save_project_state(project_state)
            logger.info(f"Project {project_id} beralih status menjadi 'running'")
            
            # Pancarkan event project_status running
            await event_bus.publish(
                project_id,
                SigmaEvent(
                    event_id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type="project_status",
                    payload={"project_id": project_id, "status": "running"}
                )
            )

        subject = "pengembangan modul"
        if project_state:
            subject = project_state.description or project_state.name

        # Alur agent: Manager -> PromptEngineer -> Coder -> Reviewer -> Tester -> Integrator
        workflow = [
            (AgentName.MANAGER, AgentName.PROMPT_ENGINEER, f"Menyusun rencana implementasi untuk: {subject}"),
            (AgentName.PROMPT_ENGINEER, AgentName.CODER, f"Menyusun brief teknis untuk: {subject}"),
            (AgentName.CODER, AgentName.REVIEWER, f"Mengimplementasikan modul awal untuk: {subject}"),
            (AgentName.REVIEWER, AgentName.TESTER, f"Melakukan review output implementasi untuk: {subject}"),
            (AgentName.TESTER, AgentName.INTEGRATOR, f"Menjalankan validasi sandbox untuk: {subject}"),
            (AgentName.INTEGRATOR, AgentName.LEAD_CONSULTANT, f"Menggabungkan deliverable untuk: {subject}"),
        ]

        for sender, receiver, task_desc in workflow:
            sender_agent = self.agents[sender]
            receiver_agent = self.agents[receiver]

            # 1. Update sender WORKING
            await sender_agent.update_status(AgentStatus.WORKING, task_desc, project_id=project_id)
            await event_bus.publish(
                project_id,
                SigmaEvent(
                    event_id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type="agent_status",
                    payload=(await sender_agent.get_state(project_id)).model_dump()
                )
            )

            # Kirim log pesan komunikasi antar agent
            msg = AgentMessage(
                id=str(uuid.uuid4()),
                project_id=project_id,
                message_type=MessageType.AGENT_COMM,
                content=task_desc,
                priority=MessagePriority.LOW,
                metadata=MessageMetadata(
                    sender=sender.value,
                    receiver=receiver.value,
                )
            )
            await state_manager.append_message(project_id, msg)
            await event_bus.publish(
                project_id,
                SigmaEvent(
                    event_id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type="message",
                    payload=msg.model_dump()
                )
            )

            # Gunakan delay dinamis dari settings
            await asyncio.sleep(settings.SIMULATION_STEP_DELAY_SECONDS)

            # 2. Update sender IDLE
            await sender_agent.update_status(AgentStatus.IDLE, project_id=project_id)
            await event_bus.publish(
                project_id,
                SigmaEvent(
                    event_id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type="agent_status",
                    payload=(await sender_agent.get_state(project_id)).model_dump()
                )
            )

        # Terakhir, Lead Consultant melapor ke User
        lc_agent = self.agents[AgentName.LEAD_CONSULTANT]
        report = f"Laporan: Tim agent telah menyelesaikan tugas '{subject}' dan berhasil digabungkan setelah melewati validasi Sandbox."
        await lc_agent.update_status(AgentStatus.IDLE, report, project_id=project_id)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="agent_status",
                payload=(await lc_agent.get_state(project_id)).model_dump()
            )
        )

        lc_msg = AgentMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            message_type=MessageType.AGENT_COMM,
            content=report,
            priority=MessagePriority.HIGH,
            metadata=MessageMetadata(
                sender=AgentName.LEAD_CONSULTANT.value,
                receiver="User",
            )
        )
        await state_manager.append_message(project_id, lc_msg)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="message",
                payload=lc_msg.model_dump()
            )
        )

        # Transisi running -> completed
        project_state = await state_manager.get_project_state(project_id)
        if project_state:
            project_state.status = "completed"
            await state_manager.save_project_state(project_state)
            logger.info(f"Project {project_id} telah selesai (completed)")
            
            # Pancarkan event project_status completed
            await event_bus.publish(
                project_id,
                SigmaEvent(
                    event_id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type="project_status",
                    payload={"project_id": project_id, "status": "completed"}
                )
            )

orchestrator = Orchestrator()
