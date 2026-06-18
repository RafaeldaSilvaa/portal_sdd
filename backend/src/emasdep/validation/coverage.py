"""Coverage Tracker: statement and branch coverage measurement."""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path


class CoverageTracker:
    def __init__(self, min_coverage: float = 0.95) -> None:
        self.min_coverage = min_coverage

    async def measure(self, code_artifacts: list[str], test_suite: str = "") -> float:
        """measure.

Args:
    code_artifacts: Descrição do parâmetro code_artifacts.
    test_suite: Descrição do parâmetro test_suite.

Retorna:
    Descrição do valor retornado."""
        if not code_artifacts:
            return 0.0

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            src_dir = tmp_path / "src"
            src_dir.mkdir()
            test_dir = tmp_path / "tests"
            test_dir.mkdir()
            (test_dir / "__init__.py").write_text("")

            for i, code in enumerate(code_artifacts):
                (src_dir / f"module_{i}.py").write_text(code, encoding="utf-8")

            if test_suite:
                (test_dir / "test_generated.py").write_text(test_suite, encoding="utf-8")

            env = {**os.environ, "PYTHONPATH": str(src_dir)}
            subprocess.run(
                [
                    "python", "-m", "coverage", "run",
                    "--source", str(src_dir),
                    "-m", "pytest", str(test_dir),
                ],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=120,
                env=env,
            )

            report_proc = subprocess.run(
                ["python", "-m", "coverage", "report", "--precision=2"],
                cwd=tmp_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return self._parse_coverage(report_proc.stdout)

    def _parse_coverage(self, report: str) -> float:
        """ parse coverage.

Args:
    report: Descrição do parâmetro report.

Retorna:
    Descrição do valor retornado."""
        for line in report.strip().split("\n"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    return float(parts[-1].rstrip("%")) / 100.0
                except ValueError:
                    continue
        return 0.0
