import os
import pytest
from core.sandbox import SandboxExecutor
from core.schemas import SandboxCommand

@pytest.mark.asyncio
async def test_sandbox_whitelist():
    # Setup sandbox di folder local temp
    executor = SandboxExecutor(workspace_root="./sandbox_test_dir")
    
    # 1. Perintah yang di-whitelist (misalnya python3)
    cmd_ok = SandboxCommand(command="python3", args=["-c", "print('hello')"])
    res_ok = await executor.execute(cmd_ok)
    assert "hello" in res_ok.stdout
    assert res_ok.return_code == 0
    
    # 2. Perintah yang ditolak (misalnya ls atau rm)
    cmd_bad = SandboxCommand(command="rm", args=["-rf", "/"])
    res_bad = await executor.execute(cmd_bad)
    assert "ditolak oleh whitelist Sandbox" in res_bad.stderr
    assert res_bad.return_code == 127

@pytest.mark.asyncio
async def test_sandbox_path_traversal():
    executor = SandboxExecutor(workspace_root="./sandbox_test_dir")
    
    # Coba jalankan command dengan subpath di luar workspace
    cmd = SandboxCommand(command="python3", args=["-c", "print('hack')"])
    res = await executor.execute(cmd, cwd_subpath="../../")
    assert "ditolak" in res.stderr
    assert res.return_code == 1
