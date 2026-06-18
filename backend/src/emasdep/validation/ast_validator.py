"""AST Validator: syntactic integrity gate."""

from __future__ import annotations

import ast
import subprocess
from dataclasses import dataclass, field


@dataclass
class ASTValidationResult:
    is_valid: bool
    syntax_errors: list[str] = field(default_factory=list)
    style_warnings: list[str] = field(default_factory=list)


class ASTValidator:
    def validate(self, code: str) -> bool:
        """validate.

Args:
    code: Descrição do parâmetro code.

Retorna:
    Descrição do valor retornado."""
        result = self.validate_detailed(code)
        return result.is_valid

    def validate_detailed(self, code: str) -> ASTValidationResult:
        """validate detailed.

Args:
    code: Descrição do parâmetro code.

Retorna:
    Descrição do valor retornado."""
        result = ASTValidationResult(is_valid=True)

        try:
            ast.parse(code)
        except SyntaxError as e:
            result.is_valid = False
            result.syntax_errors.append(f"Syntax error: {e}")

        return result

    def validate_with_ruff(self, code: str) -> ASTValidationResult:
        """validate with ruff.

Args:
    code: Descrição do parâmetro code.

Retorna:
    Descrição do valor retornado."""
        result = self.validate_detailed(code)
        if not result.is_valid:
            return result

        proc = subprocess.run(
            ["ruff", "check", "--select=E,F,I,N,W,UP,RUF", "-"],
            input=code,
            capture_output=True,
            text=True,
            timeout=30,
        )

        if proc.returncode != 0:
            result.is_valid = False
            for line in proc.stdout.strip().split("\n"):
                if line.strip():
                    result.style_warnings.append(line.strip())

        return result

    def validate_with_mypy(self, code: str) -> ASTValidationResult:
        """validate with mypy.

Args:
    code: Descrição do parâmetro code.

Retorna:
    Descrição do valor retornado."""
        import tempfile
        from pathlib import Path

        result = self.validate_detailed(code)
        if not result.is_valid:
            return result

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            tmp_path = f.name

        try:
            proc = subprocess.run(
                ["mypy", "--strict", tmp_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if proc.returncode != 0:
                result.is_valid = False
                for line in proc.stdout.strip().split("\n"):
                    if line.strip() and ":" in line:
                        result.style_warnings.append(line.strip())
        finally:
            Path(tmp_path).unlink(missing_ok=True)

        return result
