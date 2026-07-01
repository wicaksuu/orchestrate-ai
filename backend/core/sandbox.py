import os
import re
import asyncio
import shlex
import time
import logging
import subprocess
from typing import List, Tuple, Optional
from core.schemas import SandboxCommand, SandboxResult
from config import settings

logger = logging.getLogger(__name__)

# === DYNAMIC ALLOWLIST ===
# Command yang diperbolehkan dieksekusi oleh LLM agent.
# Mencakup tool development umum agar sistem tetap powerful.
COMMAND_ALLOWLIST = {
    # Kompilasi & Build
    "gcc", "g++", "make", "cmake", "cargo", "go", "rustc", "javac",
    "arm-none-eabi-gcc", "arm-none-eabi-g++", "arm-none-eabi-objdump",
    "arm-none-eabi-objcopy", "arm-none-eabi-size",
    # JavaScript / Node
    "node", "npm", "npx", "yarn", "pnpm", "tsc", "eslint", "prettier",
    # Python
    "python3", "python", "pip", "pip3", "pytest", "mypy", "ruff", "black",
    "flake8", "isort", "poetry", "uv",
    # Utilitas file aman
    "cat", "head", "tail", "wc", "sort", "uniq", "diff", "find", "grep",
    "ls", "tree", "mkdir", "cp", "mv", "touch", "echo", "printf",
    # Git (read-only + commit)
    "git",
    # Docker (build only)
    "docker",
    # Lainnya
    "bash", "sh", "env", "which", "whoami", "pwd", "date",
    "tar", "zip", "unzip", "gzip", "gunzip",
    "sed", "awk", "xargs", "jq",
    "chmod",
}

# === DENY LIST ===
# Pattern regex yang SELALU diblokir, apapun command-nya.
# Ini adalah lapisan keamanan terakhir untuk mencegah aksi destruktif.
COMMAND_DENYLIST_PATTERNS = [
    # Hapus rekursif di root/parent
    r'\brm\s+.*-[a-zA-Z]*r[a-zA-Z]*f\b.*\s+/',
    r'\brm\s+.*-[a-zA-Z]*f[a-zA-Z]*r\b.*\s+/',
    r'\brm\s+-rf\s+/',
    r'\brm\s+-rf\s+\.\.',
    # Pipe download ke shell
    r'\bcurl\b.*\|\s*(ba)?sh',
    r'\bwget\b.*\|\s*(ba)?sh',
    r'\bcurl\b.*\|\s*python',
    r'\bwget\b.*\|\s*python',
    # Privilege escalation
    r'\bsudo\b',
    r'\bsu\s+-',
    r'\bchmod\s+777\s+/',
    r'\bchown\b.*/',
    # Disk destruction
    r'\bdd\s+if=',
    r'\bmkfs\b',
    r'\bfdisk\b',
    # Network exfiltration
    r'\bnc\s+-[a-zA-Z]*l',  # netcat listener
    r'\bnetcat\b',
    # Overwrite system files
    r'>\s*/etc/',
    r'>\s*/usr/',
    r'>\s*/bin/',
    r'>\s*/sbin/',
    r'>\s*/var/',
    # Fork bomb
    r':\(\)\{.*\}',
    # Shutdown/reboot
    r'\bshutdown\b',
    r'\breboot\b',
    r'\bhalt\b',
    r'\bpoweroff\b',
    # Kill all
    r'\bkillall\b',
    r'\bkill\s+-9\s+-1',
    # Env exfiltration via curl
    r'\benv\b.*\|\s*curl',
    r'\bprintenv\b.*\|\s*curl',
]

# Pre-compile deny patterns untuk performa
_DENY_PATTERNS_COMPILED = [re.compile(p, re.IGNORECASE) for p in COMMAND_DENYLIST_PATTERNS]


def validate_command(command_str: str) -> Tuple[bool, str]:
    """
    Memvalidasi sebuah command string terhadap allowlist dan denylist.

    Returns:
        Tuple (is_allowed, reason)
        - (True, "") jika command diizinkan
        - (False, reason) jika command ditolak
    """
    command_str = command_str.strip()
    if not command_str:
        return False, "Command kosong."

    # 1. Cek deny patterns terlebih dahulu (prioritas tertinggi)
    for pattern in _DENY_PATTERNS_COMPILED:
        if pattern.search(command_str):
            return False, f"Command ditolak: cocok dengan pola berbahaya '{pattern.pattern}'."

    # 2. Parse command untuk mendapatkan executable utama
    try:
        parts = shlex.split(command_str)
    except ValueError as e:
        return False, f"Command tidak bisa di-parse: {e}"

    if not parts:
        return False, "Command kosong setelah parsing."

    executable = os.path.basename(parts[0])

    # 3. Cek allowlist
    if executable not in COMMAND_ALLOWLIST:
        return False, f"Command '{executable}' tidak ada di allowlist. Command yang diizinkan: {', '.join(sorted(COMMAND_ALLOWLIST))}."

    return True, ""


def validate_command_path(command_str: str, workspace_path: str) -> Tuple[bool, str]:
    """
    Memvalidasi bahwa argumen path dalam command tidak keluar dari workspace.
    Ini adalah lapisan tambahan di atas validate_command().

    Returns:
        Tuple (is_safe, reason)
    """
    try:
        parts = shlex.split(command_str)
    except ValueError:
        return False, "Command tidak bisa di-parse."

    ws_abs = os.path.abspath(workspace_path)

    for arg in parts[1:]:
        # Cek hanya argumen yang terlihat seperti path
        if arg.startswith('/') or '..' in arg:
            resolved = os.path.abspath(os.path.join(workspace_path, arg))
            if not resolved.startswith(ws_abs):
                return False, f"Argumen '{arg}' mengarah ke luar workspace ({ws_abs})."

    return True, ""


class SandboxExecutor:
    """SandboxExecutor mengamankan dan menjalankan perintah development yang diizinkan."""
    def __init__(self, workspace_root: str = settings.WORKSPACE_ROOT):
        self.workspace_root = os.path.abspath(workspace_root)
        # Pastikan direktori workspace ada (bisa gagal di lokal jika path Docker-only)
        try:
            os.makedirs(self.workspace_root, exist_ok=True)
        except OSError:
            pass
        # Audit log in-memory (bisa di-query untuk debugging)
        self.audit_log: List[dict] = []

    def is_safe_path(self, path: str, workspace_root: str = None) -> bool:
        """Memastikan path berada di bawah workspace_root."""
        root = workspace_root or self.workspace_root
        abs_path = os.path.abspath(path)
        return abs_path.startswith(root)

    def _log_audit(self, command: str, workspace: str, result_code: int,
                   duration_ms: float, status: str, detail: str = ""):
        """Mencatat setiap eksekusi command ke audit log."""
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "command": command,
            "workspace": workspace,
            "return_code": result_code,
            "duration_ms": round(duration_ms, 2),
            "status": status,
            "detail": detail[:500],  # Batasi panjang detail
        }
        self.audit_log.append(entry)
        # Batasi ukuran audit log di memori (simpan 1000 entry terakhir)
        if len(self.audit_log) > 1000:
            self.audit_log = self.audit_log[-1000:]
        logger.info(f"[AUDIT] {status}: {command} (rc={result_code}, {duration_ms:.0f}ms)")

    async def execute(self, cmd: SandboxCommand, cwd_subpath: str = "", project_id: str = None) -> SandboxResult:
        """Menjalankan perintah yang di-allowlist di dalam sandbox secara asinkron."""
        # 1. Validasi allowlist
        if cmd.command not in COMMAND_ALLOWLIST:
            logger.warning(f"Percobaan menjalankan command yang tidak di-allowlist: {cmd.command}")
            self._log_audit(cmd.command, self.workspace_root, 127, 0.0, "DENIED",
                            f"Command '{cmd.command}' tidak ada di allowlist.")
            return SandboxResult(
                stdout="",
                stderr=f"Command '{cmd.command}' ditolak oleh allowlist Sandbox.",
                return_code=127,
                duration_ms=0.0
            )

        # 2. Tentukan workspace root (dukungan external_path per proyek)
        current_workspace_root = self.workspace_root
        if project_id:
            from core.state_manager import state_manager
            proj_state = await state_manager.get_project_state(project_id)
            if proj_state and proj_state.external_path:
                current_workspace_root = os.path.abspath(proj_state.external_path)
                os.makedirs(current_workspace_root, exist_ok=True)
            else:
                current_workspace_root = os.path.abspath(os.path.join(self.workspace_root, project_id))
                os.makedirs(current_workspace_root, exist_ok=True)

        # 3. Validasi working directory
        cwd_path = os.path.abspath(os.path.join(current_workspace_root, cwd_subpath))
        if not self.is_safe_path(cwd_path, current_workspace_root):
            logger.warning(f"Percobaan directory traversal terdeteksi: {cwd_path}")
            self._log_audit(cmd.command, current_workspace_root, 1, 0.0, "DENIED",
                            f"Path traversal: {cwd_path}")
            return SandboxResult(
                stdout="",
                stderr="Akses direktori di luar WORKSPACE_ROOT ditolak.",
                return_code=1,
                duration_ms=0.0
            )

        # 4. Eksekusi program secara asinkron
        start_time = time.time()
        full_cmd_str = f"{cmd.command} {' '.join(cmd.args)}"

        try:
            proc = await asyncio.create_subprocess_exec(
                cmd.command,
                *cmd.args,
                cwd=cwd_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=cmd.timeout
                )
                stdout = stdout_bytes.decode('utf-8', errors='replace')
                stderr = stderr_bytes.decode('utf-8', errors='replace')
                return_code = proc.returncode if proc.returncode is not None else 0
            except asyncio.TimeoutError:
                try:
                    proc.kill()
                    await proc.wait()
                except ProcessLookupError:
                    pass
                duration_ms = (time.time() - start_time) * 1000.0
                self._log_audit(full_cmd_str, current_workspace_root, -1, duration_ms,
                                "TIMEOUT", f"Timeout setelah {cmd.timeout}s")
                return SandboxResult(
                    stdout="",
                    stderr=f"Perintah dibatalkan karena timeout ({cmd.timeout} detik).",
                    return_code=-1,
                    duration_ms=duration_ms
                )

            duration_ms = (time.time() - start_time) * 1000.0
            status = "SUCCESS" if return_code == 0 else "FAILED"
            self._log_audit(full_cmd_str, current_workspace_root, return_code, duration_ms,
                            status, stderr[:200] if return_code != 0 else "")
            return SandboxResult(
                stdout=stdout,
                stderr=stderr,
                return_code=return_code,
                duration_ms=duration_ms
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            self._log_audit(full_cmd_str, current_workspace_root, 1, duration_ms,
                            "ERROR", str(e))
            return SandboxResult(
                stdout="",
                stderr=f"Gagal mengeksekusi perintah: {str(e)}",
                return_code=1,
                duration_ms=duration_ms
            )

    def execute_shell_safe_sync(self, command_str: str, workspace_path: str,
                                timeout: int = 60) -> SandboxResult:
        """
        Menjalankan command string secara aman (SYNCHRONOUS).
        Parse dengan shlex, validasi allowlist+denylist, lalu execute tanpa shell=True.

        Ini adalah pengganti langsung untuk subprocess.run(shell=True) di utils.py.
        """
        start_time = time.time()

        # 1. Validasi command
        is_allowed, reason = validate_command(command_str)
        if not is_allowed:
            self._log_audit(command_str, workspace_path, 127, 0.0, "DENIED", reason)
            return SandboxResult(
                stdout="",
                stderr=f"Command ditolak: {reason}",
                return_code=127,
                duration_ms=0.0
            )

        # 2. Validasi path args
        is_safe, path_reason = validate_command_path(command_str, workspace_path)
        if not is_safe:
            self._log_audit(command_str, workspace_path, 1, 0.0, "DENIED", path_reason)
            return SandboxResult(
                stdout="",
                stderr=f"Command ditolak: {path_reason}",
                return_code=1,
                duration_ms=0.0
            )

        # 3. Parse dan execute tanpa shell=True
        try:
            parts = shlex.split(command_str)
        except ValueError as e:
            self._log_audit(command_str, workspace_path, 1, 0.0, "ERROR", str(e))
            return SandboxResult(
                stdout="",
                stderr=f"Gagal mem-parse command: {e}",
                return_code=1,
                duration_ms=0.0
            )

        os.makedirs(workspace_path, exist_ok=True)

        try:
            result = subprocess.run(
                parts,
                cwd=workspace_path,
                shell=False,  # PENTING: tidak pakai shell=True
                capture_output=True,
                text=True,
                timeout=timeout
            )

            duration_ms = (time.time() - start_time) * 1000.0
            status = "SUCCESS" if result.returncode == 0 else "FAILED"
            self._log_audit(command_str, workspace_path, result.returncode, duration_ms,
                            status, result.stderr[:200] if result.returncode != 0 else "")

            return SandboxResult(
                stdout=result.stdout,
                stderr=result.stderr,
                return_code=result.returncode,
                duration_ms=duration_ms
            )

        except subprocess.TimeoutExpired:
            duration_ms = (time.time() - start_time) * 1000.0
            self._log_audit(command_str, workspace_path, -1, duration_ms,
                            "TIMEOUT", f"Timeout setelah {timeout}s")
            return SandboxResult(
                stdout="",
                stderr=f"Command timeout setelah {timeout} detik.",
                return_code=-1,
                duration_ms=duration_ms
            )

        except FileNotFoundError:
            duration_ms = (time.time() - start_time) * 1000.0
            self._log_audit(command_str, workspace_path, 127, duration_ms,
                            "NOT_FOUND", f"Executable '{parts[0]}' tidak ditemukan.")
            return SandboxResult(
                stdout="",
                stderr=f"Executable '{parts[0]}' tidak ditemukan di sistem.",
                return_code=127,
                duration_ms=duration_ms
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000.0
            self._log_audit(command_str, workspace_path, 1, duration_ms, "ERROR", str(e))
            return SandboxResult(
                stdout="",
                stderr=f"Gagal mengeksekusi: {str(e)}",
                return_code=1,
                duration_ms=duration_ms
            )


sandbox_executor = SandboxExecutor()
