"""Sandboxed code executor with container isolation."""

from __future__ import annotations

import asyncio
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class ExecutionResult:
    success: bool
    stdout: str
    stderr: str
    return_code: int
    duration_ms: int


class SandboxExecutor:
    def __init__(self, sandbox_type: str = "none", image: str = "python:3.12-slim"):
        self.sandbox_type = sandbox_type
        self.image = image

    async def execute(self, code: str, test_command: str = "pytest -x tests/") -> ExecutionResult:
        if self.sandbox_type == "none":
            return await self._local_execute(code, test_command)
        return await self._docker_execute(code, test_command)

    async def _local_execute(self, code: str, test_command: str) -> ExecutionResult:
        import time
        start = time.monotonic()

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            (src_dir / "code.py").write_text(code, encoding="utf-8")

            test_dir = tmp_path / "tests"
            test_dir.mkdir()
            (test_dir / "__init__.py").write_text("", encoding="utf-8")

            proc = await asyncio.create_subprocess_shell(
                test_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=tmpdir,
            )
            stdout, stderr = await proc.communicate()
            duration = int((time.monotonic() - start) * 1000)

            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                return_code=proc.returncode or 0,
                duration_ms=duration,
            )

    async def _docker_execute(self, code: str, test_command: str) -> ExecutionResult:
        import time
        start = time.monotonic()

        with tempfile.TemporaryDirectory() as tmpdir:
            (Path(tmpdir) / "code.py").write_text(code, encoding="utf-8")

            cmd = [
                "docker", "run", "--rm",
                "--network", "none",
                "-v", f"{tmpdir}:/workspace",
                self.image,
                "sh", "-c", f"cd /workspace && {test_command}",
            ]

            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            duration = int((time.monotonic() - start) * 1000)

            return ExecutionResult(
                success=proc.returncode == 0,
                stdout=stdout.decode() if stdout else "",
                stderr=stderr.decode() if stderr else "",
                return_code=proc.returncode or 0,
                duration_ms=duration,
            )
