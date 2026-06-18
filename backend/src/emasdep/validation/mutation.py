"""Mutation Testing Gate: validates test suite quality."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from ..core.types import MutationResult


class MutationValidator:
    def __init__(self, min_score: float = 0.85) -> None:
        self.min_score = min_score

    async def validate(
        self,
        code_artifacts: dict[str, str],
        test_suite: str,
    ) -> MutationResult:
        if not code_artifacts:
            return MutationResult(
                mutation_score=0.0,
                total_mutants=0,
                killed_mutants=0,
                survived_mutants=0,
                passed_minimum=False,
            )

        return await self._run_mutmut(code_artifacts, test_suite)

    async def _run_mutmut(self, code_artifacts: dict, test_suite: str) -> MutationResult:
        """ run mutmut.

Args:
    code_artifacts: Descrição do parâmetro code_artifacts.
    test_suite: Descrição do parâmetro test_suite.

Retorna:
    Descrição do valor retornado."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            test_dir = tmp_path / "tests"
            test_dir.mkdir()
            (test_dir / "__init__.py").write_text("")

            for filename, content in code_artifacts.items():
                target = src_dir / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")

            (test_dir / "test_generated.py").write_text(
                test_suite, encoding="utf-8"
            )

            env = {**os.environ, "PYTHONPATH": str(src_dir)}
            result = subprocess.run(
                ["mutmut", "run", "--paths-to-mutate", str(src_dir)],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=300,
                env=env,
            )

            return self._parse_mutmut_output(result.stdout, result.returncode)

    def _parse_mutmut_output(self, output: str, returncode: int) -> MutationResult:
        """ parse mutmut output.

Args:
    output: Descrição do parâmetro output.
    returncode: Descrição do parâmetro returncode.

Retorna:
    Descrição do valor retornado."""
        import re

        score_match = re.search(r"(\d+\.\d+)\%", output)
        score = float(score_match.group(1)) / 100.0 if score_match else 0.0

        killed = len(re.findall(r"^--- killed", output, re.MULTILINE))
        survived = len(re.findall(r"^--- survived", output, re.MULTILINE))
        total = killed + survived

        return MutationResult(
            mutation_score=score,
            total_mutants=total,
            killed_mutants=killed,
            survived_mutants=survived,
            passed_minimum=score >= self.min_score,
        )

    async def analyze_mutation_weaknesses(self, code: str, tests: str) -> list[str]:
        """analyze mutation weaknesses.

Args:
    code: Descrição do parâmetro code.
    tests: Descrição do parâmetro tests.

Retorna:
    Descrição do valor retornado."""
        result = await self._run_mutmut({"target.py": code}, tests)

        weaknesses: list[str] = []
        if not result.passed_minimum:
            weaknesses.append(
                f"Mutation score {result.mutation_score:.2%} below "
                f"minimum {self.min_score:.0%}"
            )
            if result.survived_mutants > 0:
                weaknesses.append(
                    f"{result.survived_mutants} mutants survived testing"
                )

        return weaknesses
