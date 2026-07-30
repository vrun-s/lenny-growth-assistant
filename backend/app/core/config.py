from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Lenny Growth Assistant"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = ["http://localhost:5173"]
    database_url: str = "postgresql+psycopg://lenny:lenny@localhost:5432/lenny_growth_assistant"

    llm_provider: Literal["anthropic", "ollama"] = "anthropic"
    anthropic_api_key: str | None = None
    anthropic_model: str = "claude-sonnet-4-5"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3-coder"
    harness_timeout_seconds: int = 30

    @model_validator(mode="after")
    def _require_anthropic_key(self) -> "Settings":
        if self.llm_provider == "anthropic" and not self.anthropic_api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY is required when LLM_PROVIDER=anthropic. "
                "Set it in the environment or .env file."
            )
        return self

    @property
    def harness_base_url(self) -> str | None:
        return self.ollama_base_url if self.llm_provider == "ollama" else None

    @property
    def harness_model(self) -> str:
        return self.ollama_model if self.llm_provider == "ollama" else self.anthropic_model

    @property
    def harness_api_key(self) -> str:
        if self.llm_provider == "ollama":
            return "ollama"  # required by the client, ignored by Ollama
        assert self.anthropic_api_key is not None  # enforced by the validator above
        return self.anthropic_api_key


@lru_cache
def get_settings() -> Settings:
    return Settings()
