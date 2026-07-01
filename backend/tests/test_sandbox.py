import os
import pytest
from core.sandbox import SandboxExecutor, COMMAND_ALLOWLIST, validate_command
from core.schemas import SandboxCommand

@pytest.mark.asyncio
async def test_sandbox_allowlist():
    # Setup sandbox di folder local temp
    executor = SandboxExecutor(workspace_root="./sandbox_test_dir")
    
    # 1. Perintah yang di-allowlist (misalnya python3)
    cmd_ok = SandboxCommand(command="python3", args=["-c", "print('hello')"])
    res_ok = await executor.execute(cmd_ok)
    assert "hello" in res_ok.stdout
    assert res_ok.return_code == 0
    
    # 2. Perintah yang ditolak (misalnya rm)
    cmd_bad = SandboxCommand(command="rm", args=["-rf", "/"])
    res_bad = await executor.execute(cmd_bad)
    assert "ditolak oleh allowlist Sandbox" in res_bad.stderr
    assert res_bad.return_code == 127

@pytest.mark.asyncio
async def test_sandbox_path_traversal():
    executor = SandboxExecutor(workspace_root="./sandbox_test_dir")
    
    # Coba jalankan command dengan subpath di luar workspace
    cmd = SandboxCommand(command="python3", args=["-c", "print('hack')"])
    res = await executor.execute(cmd, cwd_subpath="../../")
    assert "ditolak" in res.stderr
    assert res.return_code == 1

@pytest.mark.asyncio
async def test_sandbox_expanded_allowlist():
    """Test bahwa command development umum ada di allowlist."""
    dev_tools = ["npm", "pip", "node", "gcc", "make", "pytest", "cargo", "go", "git"]
    for tool in dev_tools:
        assert tool in COMMAND_ALLOWLIST, f"{tool} seharusnya ada di COMMAND_ALLOWLIST"

@pytest.mark.asyncio
async def test_sandbox_audit_log():
    """Test bahwa audit log tercatat setelah eksekusi."""
    executor = SandboxExecutor(workspace_root="./sandbox_test_dir")
    executor.audit_log.clear()
    
    cmd = SandboxCommand(command="python3", args=["-c", "print('audit')"])
    await executor.execute(cmd)
    
    assert len(executor.audit_log) == 1
    assert executor.audit_log[0]["status"] == "SUCCESS"
    assert "python3" in executor.audit_log[0]["command"]

def test_validate_command_deny_patterns():
    """Test bahwa denylist patterns bekerja."""
    # Semua ini harus ditolak
    denied_commands = [
        "sudo apt install vim",
        "shutdown -h now",
        "reboot",
    ]
    for cmd in denied_commands:
        is_allowed, reason = validate_command(cmd)
        assert not is_allowed, f"'{cmd}' seharusnya ditolak: {reason}"

