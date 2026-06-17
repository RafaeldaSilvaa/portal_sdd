"""Transactional Self-Healing Engine with git-like state isolation."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from ..core.types import CodePatchSnapshot
from .snapshot import SnapshotManager


@dataclass
class HealingResult:
    success: bool
    snapshot: CodePatchSnapshot
    message: str = ""


class HealingEngine:
    def __init__(
        self,
        max_attempts: int = 3,
        snapshot_manager: SnapshotManager | None = None,
    ):
        self.max_attempts = max_attempts
        self._snapshots = snapshot_manager or SnapshotManager()

    async def attempt_heal(
        self,
        filepath: str,
        code_content: str,
        test_command: str = "pytest -x",
    ) -> HealingResult:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_file = tmp_path / filepath

            src_file.parent.mkdir(parents=True, exist_ok=True)
            src_file.write_text(code_content, encoding="utf-8")

            snapshot = CodePatchSnapshot.create(
                filepath=Path(filepath),
                contents=code_content,
            )

            result = subprocess.run(
                test_command.split(),
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                self._snapshots.save(snapshot)
                return HealingResult(
                    success=True,
                    snapshot=snapshot,
                    message="Tests passed",
                )

            snapshot.crash_log = result.stderr[:2000] if result.stderr else result.stdout[:2000]

            return HealingResult(
                success=False,
                snapshot=snapshot,
                message=result.stderr[:500] if result.stderr else "Test failure",
            )

    def rollback(self, snapshot: CodePatchSnapshot) -> str:
        return self._snapshots.restore(snapshot)
