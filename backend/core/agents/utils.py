import os
import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

def parse_and_save_llm_files(llm_response: str, workspace_path: str) -> List[str]:
    """
    Mem-parsing teks dari LLM yang memiliki format:
    # FILE: path/to/file.ext
    ```language
    content
    ```
    Lalu menyimpan file-file tersebut secara fisik ke workspace_path.
    Mengembalikan list nama file yang berhasil disimpan.
    """
    saved_files = []
    
    # Regex untuk menangkap nama file dan blok kode di bawahnya
    # Mendukung format: 
    # # FILE: src/main.c
    # ```c
    # code...
    # ```
    # ATAU sekadar blok tanpa bahasa: ```\n code \n```
    pattern = re.compile(
        r'#\s*FILE:\s*([^\r\n]+)\s*[\r\n]+```[a-zA-Z0-9_-]*[\r\n]+(.*?)```',
        re.DOTALL | re.IGNORECASE
    )
    
    matches = pattern.finditer(llm_response)
    for match in matches:
        file_path_raw = match.group(1).strip()
        file_content = match.group(2)
        saved = _save_file(workspace_path, file_path_raw, file_content)
        if saved:
            saved_files.append(saved)

    # Fallback untuk LLM yang menaruh "# FILE:" sebagai baris pertama di dalam blok kode.
    code_block_pattern = re.compile(
        r'```[a-zA-Z0-9_-]*[\r\n]+(.*?)```',
        re.DOTALL | re.IGNORECASE
    )
    for match in code_block_pattern.finditer(llm_response):
        block_content = match.group(1)
        lines = block_content.splitlines()
        if not lines:
            continue
        header = lines[0].strip()
        if not header.lower().startswith("# file:"):
            continue
        file_path_raw = header.split(":", 1)[1].strip()
        file_content = "\n".join(lines[1:])
        saved = _save_file(workspace_path, file_path_raw, file_content)
        if saved and saved not in saved_files:
            saved_files.append(saved)

    return saved_files


def _save_file(workspace_path: str, file_path_raw: str, file_content: str) -> str | None:
    """Menyimpan satu file hasil LLM setelah validasi path."""
    file_path_raw = file_path_raw.strip()
    if not file_path_raw:
        return None

    # Cegah path traversal
    file_path_safe = file_path_raw.lstrip('/')
    if '..' in file_path_safe:
        logger.warning(f"Melewatkan file berbahaya dengan traversal: {file_path_raw}")
        return None

    full_path = os.path.abspath(os.path.join(workspace_path, file_path_safe))

    # Validasi kembali path tetap berada dalam workspace
    if not full_path.startswith(os.path.abspath(workspace_path)):
        logger.warning(f"Melewatkan file di luar workspace: {file_path_raw}")
        return None

    # Pastikan direktori ada
    os.makedirs(os.path.dirname(full_path), exist_ok=True)

    try:
        with open(full_path, 'w', encoding='utf-8') as f:
            f.write(file_content)
        logger.info(f"Berhasil menyimpan file dari LLM: {file_path_safe}")
        return file_path_safe
    except Exception as e:
        logger.error(f"Gagal menyimpan file {file_path_safe}: {e}")
        return None

def parse_and_execute_llm_commands(llm_response: str, workspace_path: str) -> str:
    """
    DEPRECATED: Gunakan secure_execute_llm_commands() sebagai gantinya.
    Fungsi ini disimpan untuk backward compatibility tapi sekarang
    men-delegasi ke secure_execute_llm_commands().
    """
    return secure_execute_llm_commands(llm_response, workspace_path)


def secure_execute_llm_commands(llm_response: str, workspace_path: str) -> str:
    """
    Mem-parsing perintah terminal yang diawali dengan '# CMD: '
    dan menjalankannya secara AMAN melalui SandboxExecutor.

    Perbedaan dengan versi lama:
    - Tidak menggunakan shell=True (mencegah shell injection)
    - Semua command divalidasi melalui allowlist + denylist
    - Audit log tercatat untuk setiap eksekusi
    - Path traversal dicegah

    Mengembalikan log hasil STDOUT dan STDERR untuk diumpankan kembali ke agen.
    """
    from core.sandbox import sandbox_executor

    execution_logs = []

    # Cari baris yang diawali dengan # CMD:
    pattern = re.compile(r'#\s*CMD:\s*([^\r\n]+)', re.IGNORECASE)
    commands = pattern.findall(llm_response)

    for cmd in commands:
        cmd = cmd.strip()
        if not cmd:
            continue

        logger.info(f"Mengeksekusi perintah aman dari LLM: {cmd} di {workspace_path}")
        execution_logs.append(f"--- EXECUTION LOG FOR: `{cmd}` ---")

        result = sandbox_executor.execute_shell_safe_sync(
            command_str=cmd,
            workspace_path=workspace_path,
            timeout=60
        )

        if result.stdout.strip():
            execution_logs.append(f"STDOUT:\n{result.stdout.strip()}")
        if result.stderr.strip():
            execution_logs.append(f"STDERR:\n{result.stderr.strip()}")

        if result.return_code == 0:
            execution_logs.append("STATUS: SUCCESS")
        elif result.return_code == 127:
            execution_logs.append(f"STATUS: DENIED - {result.stderr.strip()}")
        elif result.return_code == -1:
            execution_logs.append(f"STATUS: FAILED - Command timeout.")
        else:
            execution_logs.append(f"STATUS: FAILED with exit code {result.return_code}")

        execution_logs.append("--------------------------------------")

    return "\n".join(execution_logs)
