import pytest
from emasdep.validation.ast_validator import ASTValidator


class TestASTValidator:
    @pytest.fixture
    def validator(self):
        return ASTValidator()

    def test_valid_python_code_returns_true(self, validator):
        code = "def hello() -> str:\n    return 'world'\n"
        assert validator.validate(code) is True

    def test_invalid_syntax_returns_false(self, validator):
        code = "def broken(:"
        assert validator.validate(code) is False

    def test_detailed_result_for_valid_code(self, validator):
        code = "x = 1"
        result = validator.validate_detailed(code)
        assert result.is_valid is True
        assert len(result.syntax_errors) == 0

    def test_detailed_result_for_invalid_code(self, validator):
        code = "if True"
        result = validator.validate_detailed(code)
        assert result.is_valid is False
        assert len(result.syntax_errors) > 0

    def test_empty_code_is_valid(self, validator):
        assert validator.validate("") is True

    def test_imports_are_valid(self, validator):
        code = "import os\nfrom pathlib import Path\n"
        assert validator.validate(code) is True

    def test_class_definition_is_valid(self, validator):
        code = "class MyClass:\n    def method(self) -> int:\n        return 42\n"
        assert validator.validate(code) is True
