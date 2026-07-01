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
from core.db import database_manager
from config import settings

# Import agents
from core.agents.lead_consultant import LeadConsultantAgent
from core.agents.manager import ManagerAgent
from core.agents.prompt_engineer import PromptEngineerAgent
from core.agents.coder import CoderAgent
from core.agents.reviewer import ReviewerAgent
from core.agents.tester import TesterAgent
from core.agents.integrator import IntegratorAgent
from core.agents.ui_ux_designer import UiUxDesignerAgent

logger = logging.getLogger(__name__)

class Orchestrator:
    """Orchestrator mengelola siklus hidup eksekusi multi-agent dan orkestrasinya."""
    def __init__(self):
        self.agents = {
            AgentName.LEAD_CONSULTANT: LeadConsultantAgent(),
            AgentName.MANAGER: ManagerAgent(),
            AgentName.PROMPT_ENGINEER: PromptEngineerAgent(),
            AgentName.UI_UX_DESIGNER: UiUxDesignerAgent(),
            AgentName.CODER: CoderAgent(),
            AgentName.REVIEWER: ReviewerAgent(),
            AgentName.TESTER: TesterAgent(),
            AgentName.INTEGRATOR: IntegratorAgent(),
        }
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.llm = None
        # Concurrency lock per project — mencegah race condition
        self._project_locks: Dict[str, asyncio.Lock] = {}

    def _get_project_lock(self, project_id: str) -> asyncio.Lock:
        """Mendapatkan atau membuat asyncio.Lock per project_id."""
        if project_id not in self._project_locks:
            self._project_locks[project_id] = asyncio.Lock()
        return self._project_locks[project_id]

    async def initialize_project(self, project_id: str):
        """Menginisialisasi status awal seluruh agent dan membuat folder workspace per proyek baru."""
        import os
        from config import settings as _settings

        # Buat folder workspace dedicated per project_id di bawah WORKSPACE_ROOT
        proj_state = await state_manager.get_project_state(project_id)
        if proj_state and proj_state.external_path:
            project_workspace = os.path.abspath(proj_state.external_path)
        else:
            project_workspace = os.path.abspath(
                os.path.join(_settings.WORKSPACE_ROOT, project_id)
            )
        try:
            os.makedirs(project_workspace, exist_ok=True)
            logger.info(f"Workspace proyek dibuat di: {project_workspace}")
        except OSError:
            logger.warning(f"Gagal membuat workspace di {project_workspace}. Ini wajar jika berjalan lokal di luar container.")

        for name, agent in self.agents.items():
            state = await state_manager.get_agent_state(name.value, project_id)
            state.status = AgentStatus.IDLE
            state.last_message = f"Agent {name.value} siap digunakan."
            state.token_count = 0
            await state_manager.save_agent_state(state, project_id)

    async def handle_user_message(self, project_id: str, content: str):
        """Menangani pesan dari user ke Lead Consultant dengan Discovery Flow State Machine."""
        lock = self._get_project_lock(project_id)
        async with lock:
            await self._handle_user_message_impl(project_id, content)

    async def _handle_user_message_impl(self, project_id: str, content: str):
        """Implementasi internal handle_user_message (dipanggil di dalam lock)."""
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

                # Jalankan workflow nyata secara background
                if project_id not in self.running_tasks or self.running_tasks[project_id].done():
                    self.running_tasks[project_id] = asyncio.create_task(
                        self.run_real_workflow(project_id)
                    )
                response_content = "Persetujuan diterima. Saya telah meminta Manager untuk memulai fase perencanaan dan eksekusi proyek."
        else:
            # Panggil LLM provider complete() untuk menghasilkan response LeadConsultant
            # Menggunakan _get_agent_llm() — single source of truth
            history_msgs = await state_manager.get_messages(project_id)
            llm_messages = []
            for msg in history_msgs[-15:]:  # batasi history
                if msg.message_type == MessageType.USER:
                    llm_messages.append({"role": "user", "content": msg.content})
                elif msg.message_type == MessageType.AGENT_COMM:
                    if msg.metadata and msg.metadata.sender == AgentName.LEAD_CONSULTANT.value:
                        llm_messages.append({"role": "assistant", "content": msg.content})
                    else:
                        sender = msg.metadata.sender if msg.metadata else "System"
                        llm_messages.append({"role": "user", "content": f"[Internal Note from {sender}]: {msg.content}"})

            try:
                llm_provider, model = await self._get_agent_llm(project_id, AgentName.LEAD_CONSULTANT)

                # Bangun konteks workspace untuk disuntikkan ke system prompt
                import os as _os
                from config import settings as _s
                if project_state.external_path:
                    ws_path = _os.path.abspath(project_state.external_path)
                else:
                    ws_path = _os.path.abspath(_os.path.join(_s.WORKSPACE_ROOT, project_id))
                try:
                    _os.makedirs(ws_path, exist_ok=True)
                except OSError:
                    pass

                workspace_info = self._get_workspace_context(ws_path)

                enriched_system_prompt = (
                    f"{lc_agent.system_prompt}\n\n"
                    f"=== KONTEKS WORKSPACE PROYEK ===\n"
                    f"Nama Proyek: {project_state.name}\n"
                    f"ID Proyek: {project_id}\n"
                    f"Path Workspace (dapat kamu akses): {ws_path}\n"
                    f"{workspace_info}\n\n"
                    f"Kamu memiliki akses PENUH ke folder workspace di atas dan DAPAT membaca, "
                    f"menganalisis, serta mendiskusikan isi file di dalamnya. "
                    f"JANGAN pernah bilang kamu tidak bisa mengakses folder pengguna."
                )

                if project_state.status == "discovery" and not is_approval:
                    manager_sys = self.agents[AgentName.MANAGER].system_prompt
                    ui_ux_sys = self.agents[AgentName.UI_UX_DESIGNER].system_prompt
                    
                    manager_provider, manager_model = await self._get_agent_llm(project_id, AgentName.MANAGER)
                    designer_provider, designer_model = await self._get_agent_llm(project_id, AgentName.UI_UX_DESIGNER)
                    
                    eval_prompt = f"User request: '{content}'. What are the critical missing requirements or technical considerations? Keep it brief and focused on your role."
                    
                    manager_coro = manager_provider.complete(
                        system_prompt=manager_sys,
                        messages=[{"role": "user", "content": eval_prompt}],
                        model=manager_model
                    )
                    designer_coro = designer_provider.complete(
                        system_prompt=ui_ux_sys,
                        messages=[{"role": "user", "content": eval_prompt}],
                        model=designer_model
                    )
                    
                    manager_resp, designer_resp = await asyncio.gather(manager_coro, designer_coro)
                    
                    manager_msg = AgentMessage(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        message_type=MessageType.AGENT_COMM,
                        content=manager_resp,
                        priority=MessagePriority.LOW,
                        metadata=MessageMetadata(sender=AgentName.MANAGER.value, receiver=AgentName.LEAD_CONSULTANT.value)
                    )
                    designer_msg = AgentMessage(
                        id=str(uuid.uuid4()),
                        project_id=project_id,
                        message_type=MessageType.AGENT_COMM,
                        content=designer_resp,
                        priority=MessagePriority.LOW,
                        metadata=MessageMetadata(sender=AgentName.UI_UX_DESIGNER.value, receiver=AgentName.LEAD_CONSULTANT.value)
                    )
                    await state_manager.append_message(project_id, manager_msg)
                    await state_manager.append_message(project_id, designer_msg)
                    
                    await event_bus.publish(project_id, SigmaEvent(event_id=str(uuid.uuid4()), project_id=project_id, event_type="message", payload=manager_msg.model_dump()))
                    await event_bus.publish(project_id, SigmaEvent(event_id=str(uuid.uuid4()), project_id=project_id, event_type="message", payload=designer_msg.model_dump()))

                    internal_discussion_context = (
                        f"\n\n[SYSTEM] To help analyze the request, the manager and designer provide the following REAL input:\n"
                        f"- Manager says: '{manager_resp}'\n"
                        f"- UI/UX Designer says: '{designer_resp}'\n"
                        f"Based on their input, CHOOSE ONLY ONE most important question to ask the user right now. Do not ask more than one question at a time."
                    )
                    enriched_system_prompt += internal_discussion_context

                response_content = await llm_provider.complete(
                    system_prompt=enriched_system_prompt,
                    messages=llm_messages,
                    model=model,
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

    async def _get_agent_llm(self, project_id: str, agent_name: AgentName) -> tuple:
        """Helper untuk mendapatkan llm_provider dan model yang tepat berdasarkan config."""
        runtime_setting = await database_manager.get_agent_ai_runtime(project_id, agent_name.value)
        llm_provider = None
        model = (
            settings.OPENAI_MODEL
            if settings.LLM_PROVIDER.lower() in {"openai", "codex"}
            else settings.DEFAULT_MODEL
        )
        if runtime_setting:
            raw_key = runtime_setting.get("api_key")
            provider_type = runtime_setting["provider"]
            if not raw_key:
                if provider_type == "gemini":
                    raw_key = settings.GEMINI_API_KEY or None
                elif provider_type == "anthropic":
                    raw_key = settings.ANTHROPIC_API_KEY or None
                elif provider_type in {"openai", "codex"}:
                    raw_key = settings.OPENAI_API_KEY or None

            from core.llm import get_llm_provider as _get_llm
            llm_provider = _get_llm(
                provider_type=provider_type,
                api_key=raw_key,
            )
            model = runtime_setting["model"]
        else:
            from core.llm import get_llm_provider as _get_llm
            llm_provider = _get_llm()

        return llm_provider, model

    def _get_workspace_context(self, ws_path: str) -> str:
        """Membangun teks konteks isi file di workspace."""
        import os as _os
        ignored_dirs = {".git", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
        file_lines = []
        for root_w, dirs_w, files_w in _os.walk(ws_path):
            dirs_w[:] = [d for d in dirs_w if d not in ignored_dirs]
            rel_root = _os.path.relpath(root_w, ws_path)
            prefix = "" if rel_root == "." else rel_root + "/"
            for d in dirs_w:
                file_lines.append(f"  📁 {prefix}{d}/")
            for f in files_w:
                try:
                    size = _os.path.getsize(_os.path.join(root_w, f))
                except OSError:
                    size = 0
                file_lines.append(f"  📄 {prefix}{f}  ({size:,} bytes)")
            if len(file_lines) > 80:
                file_lines.append("  ... (terpotong, terlalu banyak file)")
                break

        if file_lines:
            return f"Struktur folder workspace:\n" + "\n".join(file_lines)
        return "Workspace masih kosong."

    async def _mark_project_failed(self, project_id: str, reason: str) -> None:
        """Menandai project gagal dan memancarkan event status/message."""
        project_state = await state_manager.get_project_state(project_id)
        if project_state:
            project_state.status = "failed"
            await state_manager.save_project_state(project_state)

        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="project_status",
                payload={"project_id": project_id, "status": "failed", "reason": reason},
            )
        )

        failure_msg = AgentMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            message_type=MessageType.SYSTEM,
            content=f"Workflow dihentikan karena provider AI gagal: {reason}",
            priority=MessagePriority.CRITICAL,
            metadata=MessageMetadata(
                sender="System",
                receiver="User",
            )
        )
        await state_manager.append_message(project_id, failure_msg)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="message",
                payload=failure_msg.model_dump()
            )
        )

    async def _run_agent_step(self, project_id: str, sender: AgentName, receiver: AgentName,
                              task_instruction: str, previous_output: str, ws_path: str,
                              total_saved_files: list) -> str:
        """
        Menjalankan satu step agent dalam workflow: call LLM, parse/save files, execute commands.
        Mengembalikan response content dari agent, atau None jika gagal.
        """
        import os as _os
        from core.agents.utils import parse_and_save_llm_files, secure_execute_llm_commands

        sender_agent = self.agents[sender]

        # 1. Update sender WORKING
        await sender_agent.update_status(AgentStatus.WORKING, task_instruction, project_id=project_id)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="agent_status",
                payload=(await sender_agent.get_state(project_id)).model_dump()
            )
        )

        # 2. Panggil LLM Agent
        llm_provider, model = await self._get_agent_llm(project_id, sender)

        workspace_info = self._get_workspace_context(ws_path)
        enriched_system_prompt = (
            f"{sender_agent.system_prompt}\n\n"
            f"=== WORKSPACE CONTEXT ===\n"
            f"Workspace Path: {ws_path}\n"
            f"{workspace_info}\n\n"
            f"CRITICAL RULES FOR FILE CREATION/MODIFICATION AND COMMAND EXECUTION:\n"
            f"1. To create or edit a file physically on the user's system, you MUST use the exact format below.\n"
            f"The '# FILE:' line MUST be placed OUTSIDE the code block, exactly before the triple backticks:\n"
            f"# FILE: path/to/file.ext\n"
            f"```language\n"
            f"(file content)\n"
            f"```\n"
            f"2. To execute terminal/shell commands (e.g., npm install, chmod, mkdir), you MUST use this exact format:\n"
            f"# CMD: your_bash_command_here\n"
            f"All blocks prefixed with '# FILE: ' or '# CMD: ' will be automatically parsed and executed by the platform.\n"
            f"If your role is Coder, Tester, or Integrator, you MUST output at least one file block or execute a command. DO NOT just provide explanations."
        )

        # Input pesan agent berisi: instruksi spesifik + konteks dari output agen sebelumnya
        llm_messages = [
            {"role": "user", "content": f"{task_instruction}\n\n=== HASIL PEKERJAAN AGEN SEBELUMNYA ===\n{previous_output[-3000:]}"}
        ]

        max_retries = 3
        final_response = ""

        for attempt in range(max_retries):
            try:
                response_content = await llm_provider.complete(
                    system_prompt=enriched_system_prompt,
                    messages=llm_messages,
                    model=model,
                )
            except Exception as e:
                logger.error(f"Error pada {sender.value} LLM call: {e}")
                await sender_agent.update_status(
                    AgentStatus.ERROR,
                    f"Provider AI gagal: {e}",
                    project_id=project_id,
                )
                await event_bus.publish(
                    project_id,
                    SigmaEvent(
                        event_id=str(uuid.uuid4()),
                        project_id=project_id,
                        event_type="agent_status",
                        payload=(await sender_agent.get_state(project_id)).model_dump()
                    )
                )
                await self._mark_project_failed(project_id, f"{sender.value}: {e}")
                return None

            # 3. Parse dan Simpan File ke Disk
            saved_files = parse_and_save_llm_files(response_content, ws_path)
            if saved_files:
                total_saved_files.extend(saved_files)
                response_content += f"\n\n*(Platform Log: Agent ini berhasil membuat/memodifikasi file: {', '.join(saved_files)})*"

            # 3.5 Parse dan Eksekusi Perintah Terminal secara AMAN
            execution_logs = secure_execute_llm_commands(response_content, ws_path)
            if execution_logs:
                response_content += f"\n\n*(Platform Execution Log):\n{execution_logs}*"

            # Self-Healing Check
            if "STATUS: FAILED" in execution_logs and attempt < max_retries - 1:
                logger.info(f"Agent {sender.value} mengalami kegagalan eksekusi. Retrying attempt {attempt+1}")
                llm_messages.append({"role": "assistant", "content": response_content})
                llm_messages.append({
                    "role": "user",
                    "content": f"Your command execution failed.\nHere are the logs:\n{execution_logs}\n\nPlease fix the errors (e.g. install missing packages using `# CMD:`) and try again."
                })
                continue

            # Sukses atau mentok di max_retries
            final_response = response_content
            break

        # 4. Kirim log pesan komunikasi antar agent
        msg = AgentMessage(
            id=str(uuid.uuid4()),
            project_id=project_id,
            message_type=MessageType.AGENT_COMM,
            content=final_response,
            priority=MessagePriority.MEDIUM,
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

        # 5. Update sender IDLE
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

        return final_response

    async def run_real_workflow(self, project_id: str):
        """Menjalankan alur kerja pengembangan nyata menggunakan LLM per agent."""
        lock = self._get_project_lock(project_id)
        async with lock:
            try:
                await self._run_real_workflow_impl(project_id)
            except Exception as e:
                logger.error(f"Uncaught exception in workflow untuk {project_id}: {e}")
                await self._mark_project_failed(project_id, f"Internal System Error: {e}")

    async def _run_real_workflow_impl(self, project_id: str):
        """Implementasi internal workflow (dipanggil di dalam lock)."""
        logger.info(f"Memulai alur eksekusi REAL orkestrasi untuk project {project_id}")
        import os as _os

        # Transisi ke running
        project_state = await state_manager.get_project_state(project_id)
        if not project_state:
            return

        project_state.status = "running"
        await state_manager.save_project_state(project_state)
        await event_bus.publish(
            project_id,
            SigmaEvent(
                event_id=str(uuid.uuid4()),
                project_id=project_id,
                event_type="project_status",
                payload={"project_id": project_id, "status": "running"}
            )
        )

        # Siapkan direktori workspace
        if project_state.external_path:
            ws_path = _os.path.abspath(project_state.external_path)
        else:
            ws_path = _os.path.abspath(_os.path.join(settings.WORKSPACE_ROOT, project_id))
        try:
            _os.makedirs(ws_path, exist_ok=True)
        except OSError:
            pass

        subject = project_state.description or project_state.name
        total_saved_files: list[str] = []

        # === FASE 1: Manager → PromptEngineer ===
        previous_output = f"Project Context/Goal: {subject}"

        manager_output = await self._run_agent_step(
            project_id, AgentName.MANAGER, AgentName.PROMPT_ENGINEER,
            f"Please construct a comprehensive implementation plan and task breakdown for: {subject}",
            previous_output, ws_path, total_saved_files
        )
        if manager_output is None:
            return
        previous_output = manager_output

        # === FASE 2: PromptEngineer → Coder ===
        pe_output = await self._run_agent_step(
            project_id, AgentName.PROMPT_ENGINEER, AgentName.CODER,
            "Please translate the previous implementation plan into detailed technical specifications and file generation instructions.",
            previous_output, ws_path, total_saved_files
        )
        if pe_output is None:
            return
        previous_output = pe_output

        # === FASE 3: Coder → Reviewer (dengan Revision Loop) ===
        coder_output = await self._run_agent_step(
            project_id, AgentName.CODER, AgentName.REVIEWER,
            "Please generate the raw source code based on the previous technical specifications. CRITICAL: Use the exact '# FILE: filename.ext' block format.",
            previous_output, ws_path, total_saved_files
        )
        if coder_output is None:
            return

        # === REVISION LOOP: Reviewer ↔ Coder ===
        max_revisions = settings.MAX_REVISION_LOOPS
        current_code = coder_output

        for revision_round in range(max_revisions):
            # Reviewer review kode dari Coder
            reviewer_output = await self._run_agent_step(
                project_id, AgentName.REVIEWER, AgentName.TESTER,
                f"Please review the code provided by the Coder. If there are logical or syntax errors, fix them by outputting the corrected file blocks. Start your response with '# APPROVED' or '# REVISION_NEEDED'.",
                current_code, ws_path, total_saved_files
            )
            if reviewer_output is None:
                return

            # Cek apakah Reviewer meng-approve kode
            reviewer_first_line = reviewer_output.strip().split('\n')[0].strip().upper()
            is_approved = "# APPROVED" in reviewer_first_line or "APPROVED" in reviewer_first_line
            needs_revision = "# REVISION_NEEDED" in reviewer_first_line or "REVISION_NEEDED" in reviewer_first_line

            if is_approved or (not needs_revision and revision_round > 0):
                # Kode disetujui — lanjut ke Tester
                logger.info(f"Reviewer APPROVED kode di revision round {revision_round + 1}")
                await event_bus.publish(
                    project_id,
                    SigmaEvent(
                        event_id=str(uuid.uuid4()),
                        project_id=project_id,
                        event_type="revision_loop",
                        payload={
                            "round": revision_round + 1,
                            "max_rounds": max_revisions,
                            "decision": "APPROVED",
                        }
                    )
                )
                current_code = reviewer_output
                break

            # Kode butuh revisi — kirim kembali ke Coder
            logger.info(f"Reviewer REVISION_NEEDED round {revision_round + 1}/{max_revisions}")
            await event_bus.publish(
                project_id,
                SigmaEvent(
                    event_id=str(uuid.uuid4()),
                    project_id=project_id,
                    event_type="revision_loop",
                    payload={
                        "round": revision_round + 1,
                        "max_rounds": max_revisions,
                        "decision": "REVISION_NEEDED",
                    }
                )
            )

            if revision_round < max_revisions - 1:
                # Coder memperbaiki berdasarkan feedback Reviewer
                coder_fix_output = await self._run_agent_step(
                    project_id, AgentName.CODER, AgentName.REVIEWER,
                    f"The Reviewer has found issues in your code and requested revisions (round {revision_round + 2}/{max_revisions}). "
                    f"Please fix the issues described below and output the corrected code using '# FILE:' format.",
                    reviewer_output, ws_path, total_saved_files
                )
                if coder_fix_output is None:
                    return
                current_code = coder_fix_output
            else:
                # Mentok di max revisions — lanjut saja
                logger.warning(f"Max revision loops ({max_revisions}) tercapai. Melanjutkan ke Tester.")
                current_code = reviewer_output

        previous_output = current_code

        # === FASE 4: Tester ===
        tester_output = await self._run_agent_step(
            project_id, AgentName.TESTER, AgentName.INTEGRATOR,
            "Please write unit tests or a test plan for the code generated by the Reviewer/Coder.",
            previous_output, ws_path, total_saved_files
        )
        if tester_output is None:
            return
        previous_output = tester_output

        # === FASE 5: Integrator ===
        integrator_output = await self._run_agent_step(
            project_id, AgentName.INTEGRATOR, AgentName.LEAD_CONSULTANT,
            "Please provide a final integration report and compile all generated files, ensuring the structure is ready for release.",
            previous_output, ws_path, total_saved_files
        )
        if integrator_output is None:
            return

        if not total_saved_files:
            await self._mark_project_failed(
                project_id,
                "Tidak ada file yang berhasil dibuat oleh agent. Pastikan provider AI menghasilkan output dengan format '# FILE: path/to/file.ext'.",
            )
            return

        # Terakhir, Lead Consultant melapor ke User
        lc_agent = self.agents[AgentName.LEAD_CONSULTANT]
        report = f"Laporan Akhir Workflow: Seluruh tim agent telah menyelesaikan tugas '{subject}' secara nyata. Silakan periksa file yang dihasilkan di dalam workspace (bisa dilihat melalui panel 'Project Files' di UI)."
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
