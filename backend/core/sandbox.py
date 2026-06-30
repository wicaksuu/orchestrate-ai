import os
import asyncio
import time
import logging
from typing import List
from core.schemas import SandboxCommand, SandboxResult
from config import settings

logger = logging.getLogger(__name__)

# Whitelist command yang diperbolehkan di Sandbox
COMMAND_WHITELIST = {
    "arm-none-eabi-gcc",
    "arm-none-eabi-objdump",
    "gcc",
    "make",
    "python3"
}

class SandboxExecutor:
    """SandboxExecutor mengamankan dan menjalankan perintah development yang diizinkan."""
    def __init__(self, workspace_root: str = settings.WORKSPACE_ROOT):
        self.workspace_root = os.path.abspath(workspace_root)
        # Pastikan direktori workspace ada
        os.makedirs(self.workspace_root, exist_ok=True)

    def is_safe_path(self, path: str) -> bool:
        """Memastikan path berada di bawah WORKSPACE_ROOT."""
        abs_path = os.path.abspath(path)
        return abs_path.startswith(self.workspace_root)

    async def execute(self, cmd: SandboxCommand, cwd_subpath: str = "") -> SandboxResult:
        """Menjalankan perintah whitelisted di dalam sandbox secara asinkron."""
        # 1. Validasi whitelist
        if cmd.command not in COMMAND_WHITELIST:
            logger.warning(f"Percobaan menjalankan command yang tidak di-whitelist: {cmd.command}")
            return SandboxResult(
                stdout="",
                stderr=f"Command '{cmd.command}' ditolak oleh whitelist Sandbox.",
                return_code=127,
                duration_ms=0.0
            )

        # 2. Validasi working directory
        cwd_path = os.path.abspath(os.path.join(self.workspace_root, cwd_subpath))
        if not self.is_safe_path(cwd_path):
            logger.warning(f"Percobaan directory traversal terdeteksi: {cwd_path}")
            return SandboxResult(
                stdout="",
                stderr="Akses direktori di luar WORKSPACE_ROOT ditolak.",
                return_code=1,
                duration_ms=0.0
            )

        # 3. Eksekusi program secara asinkron
        start_time = time.time()
        
        try:
            # Panggil create_subprocess_exec
            proc = await asyncio.create_subprocess_exec(
                cmd.command,
                *cmd.args,
                cwd=cwd_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Batasi waktu tunggu dengan asyncio.wait_for
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=cmd.timeout
                )
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                return_code = proc.returncode if proc.returncode is not None else 0
            except asyncio.TimeoutError:
                # Jika timeout, kill subproses
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                duration_ms = (time.time() - start_time) * 1000.0
                return SandboxResult(
                    stdout="",
                    stderr=f"Perintah dibatalkan karena timeout ({cmd.timeout} detik).",
                    return_code=-1,
                    duration_ms=duration_ms
                )
            
            duration_ms = (time.time() - start_time) * 1000.0
            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            return SandboxResult(
                stdout="",
                stderr=f"Gagal mengeksekusi perintah: {str(e)}",
                return_code=1,
                duration_ms=duration_ms
            )

sandbox_executor = SandboxExecutor()
