import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_anthropic_provider_requires_api_key():
    with pytest.raises(ValidationError, match="ANTHROPIC_API_KEY"):
        Settings(llm_provider="anthropic", anthropic_api_key=None, _env_file=None)


def test_anthropic_provider_resolves_harness_config():
    settings = Settings(llm_provider="anthropic", anthropic_api_key="sk-test", _env_file=None)

    assert settings.harness_base_url is None
    assert settings.harness_model == settings.anthropic_model
    assert settings.harness_api_key == "sk-test"


def test_ollama_provider_does_not_require_api_key():
    settings = Settings(llm_provider="ollama", anthropic_api_key=None, _env_file=None)

    assert settings.harness_base_url == settings.ollama_base_url
    assert settings.harness_model == settings.ollama_model
    assert settings.harness_api_key == "ollama"
