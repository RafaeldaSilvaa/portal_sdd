import pytest
from emasdep.config import EMASDEPConfig


class TestEMASDEPConfig:
    def test_default_llm_model(self):
        config = EMASDEPConfig()
        assert config.llm_model == "gpt-4o-mini"

    def test_default_max_healing_attempts(self):
        config = EMASDEPConfig()
        assert config.max_healing_attempts == 3

    def test_default_ambiguity_threshold(self):
        config = EMASDEPConfig()
        assert config.ambiguity_threshold == 0.15

    def test_default_mutation_score(self):
        config = EMASDEPConfig()
        assert config.min_mutation_score == 0.85

    def test_default_coverage(self):
        config = EMASDEPConfig()
        assert config.min_coverage == 0.95

    def test_default_sandbox_type(self):
        config = EMASDEPConfig()
        assert config.sandbox_type == "none"

    def test_default_telemetry_enabled(self):
        config = EMASDEPConfig()
        assert config.telemetry_enabled is True

    def test_default_security_clearance(self):
        config = EMASDEPConfig()
        assert config.security_clearance == "enterprise-restricted"

    def test_default_allowed_extensions_include_py(self):
        config = EMASDEPConfig()
        assert ".py" in config.allowed_file_extensions
