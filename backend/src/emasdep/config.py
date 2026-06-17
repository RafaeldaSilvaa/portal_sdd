from pydantic import Field
from pydantic_settings import BaseSettings


class EMASDEPConfig(BaseSettings):
    model_config = {"env_prefix": "EMASDEP_", "env_file": ".env", "extra": "ignore"}

    # LLM Provider (openai, ollama, mock)
    llm_provider: str = Field(default="mock")
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="https://api.openai.com/v1")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_temperature: float = Field(default=0.0)
    llm_max_tokens: int = Field(default=8192)

    # Pipeline
    max_healing_attempts: int = Field(default=3, ge=1, le=10)
    ambiguity_threshold: float = Field(default=0.15, ge=0.0, le=1.0)
    min_mutation_score: float = Field(default=0.85, ge=0.0, le=1.0)
    min_coverage: float = Field(default=0.95, ge=0.0, le=1.0)

    # Sandbox
    sandbox_type: str = Field(default="none")
    sandbox_image: str = Field(default="python:3.12-slim")
    sandbox_timeout_seconds: int = Field(default=300)

    # Storage
    state_store_path: str = Field(default="/data/.emasdep_state")
    snapshot_path: str = Field(default="/data/.emasdep_snapshots")
    skills_path: str = Field(default="/app/skills")

    # Telemetry
    telemetry_enabled: bool = Field(default=True)
    trace_output_path: str = Field(default="/data/.emasdep_traces")

    # Security
    security_clearance: str = Field(default="enterprise-restricted")
    allow_network_access: bool = Field(default=False)
    allowed_file_extensions: list[str] = Field(default=[".py", ".md", ".yaml", ".json"])
