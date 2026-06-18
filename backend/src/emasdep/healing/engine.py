"""Transactional Self-Healing Engine with failure classification and adaptive strategy."""

from __future__ import annotations

import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from ..core.types import CodePatchSnapshot, FailureCategory
from .snapshot import SnapshotManager


@dataclass
class HealingResult:
    success: bool
    snapshot: CodePatchSnapshot
    message: str = ""
    failure_category: FailureCategory = FailureCategory.UNKNOWN


class HealingEngine:
    def __init__(
        self,
        max_attempts: int = 3,
        snapshot_manager: SnapshotManager | None = None,
    ) -> None:
        """inicializa o motor de auto-cura com limite de tentativas."""
        self.max_attempts = max_attempts
        self._snapshots = snapshot_manager or SnapshotManager()

    def classify_failure(self, stderr: str, stdout: str) -> FailureCategory:
        """classify failure.

Args:
    stderr: Descrição do parâmetro stderr.
    stdout: Descrição do parâmetro stdout.

Retorna:
    Descrição do valor retornado."""
        combined = (stderr + "\n" + stdout).lower()

        if re.search(r"(no module named|import error|cannot import)", combined):
            return FailureCategory.DEPENDENCY_FAILURE
        if re.search(r"(timeout|timed?[- ]?out|connection.*refused)", combined):
            return FailureCategory.TIMEOUT
        if re.search(r"(indentation|syntaxerror|invalid syntax|unexpected.*token)", combined):
            return FailureCategory.SCHEMA_VIOLATION
        if re.search(r"(typeerror|attributeerror|keyerror|indexerror|valueerror)", combined):
            return FailureCategory.LOGIC_ERROR
        if re.search(r"(not found|does not exist|undefined)", combined):
            return FailureCategory.HALLUCINATION

        return FailureCategory.UNKNOWN

    def select_healing_strategy(self, category: FailureCategory, attempt: int) -> str:
        """select healing strategy.

Args:
    category: Descrição do parâmetro category.
    attempt: Descrição do parâmetro attempt.

Retorna:
    Descrição do valor retornado."""
        strategies = {
            FailureCategory.HALLUCINATION: "simplify_context",
            FailureCategory.SCHEMA_VIOLATION: "retry_same",
            FailureCategory.TIMEOUT: "retry_same",
            FailureCategory.LOGIC_ERROR: "simplify_context" if attempt >= 2 else "retry_same",
            FailureCategory.DEPENDENCY_FAILURE: "replan",
            FailureCategory.UNKNOWN: "retry_same",
        }
        return strategies.get(category, "retry_same")

    async def attempt_heal(
        self,
        filepath: str,
        code_content: str,
        test_command: str = "pytest -x",
        test_content: str | None = None,
    ) -> HealingResult:
        """tenta curar um artefato de código com falha nos testes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_file = tmp_path / filepath
            src_file.parent.mkdir(parents=True, exist_ok=True)
            src_file.write_text(code_content, encoding="utf-8")

            if test_content:
                tests_dir = tmp_path / "tests"
                tests_dir.mkdir(parents=True, exist_ok=True)
                (tests_dir / "test_generated.py").write_text(test_content, encoding="utf-8")

            snapshot = CodePatchSnapshot.create(
                filepath=Path(filepath),
                contents=code_content,
            )

            import os as _os
            env = _os.environ.copy()
            env["PYTHONPATH"] = str(tmp_path)
            import sys as _sys
            use_shell = _sys.platform == "win32"
            result = subprocess.run(
                test_command if use_shell else test_command.split(),
                cwd=tmpdir,
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                shell=use_shell,
            )

            if result.returncode == 0:
                self._snapshots.save(snapshot)
                return HealingResult(
                    success=True,
                    snapshot=snapshot,
                    message="Tests passed",
                )

            crash = result.stderr[:2000] if result.stderr else result.stdout[:2000]
            snapshot.crash_log = crash

            category = self.classify_failure(result.stderr, result.stdout)
            snapshot.failure_category = category

            return HealingResult(
                success=False,
                snapshot=snapshot,
                message=crash[:500],
                failure_category=category,
            )

    def rollback(self, snapshot: CodePatchSnapshot) -> str:
        return self._snapshots.restore(snapshot)
