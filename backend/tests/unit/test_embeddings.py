import httpx
import pytest

from app.core.config import Settings
from app.infrastructure.vectorstore.embeddings import EMBEDDING_MODEL, OllamaEmbedder


def _settings() -> Settings:
    return Settings(llm_provider="anthropic", anthropic_api_key="sk-test", _env_file=None)


def test_embed_posts_to_ollama_and_returns_the_vector(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def fake_post(url, json, timeout):
        captured["url"] = url
        captured["json"] = json
        return httpx.Response(
            200, json={"embedding": [0.1, 0.2, 0.3]}, request=httpx.Request("POST", url)
        )

    monkeypatch.setattr(httpx, "post", fake_post)

    embedder = OllamaEmbedder(settings=_settings())
    vector = embedder.embed("hello world")

    assert vector == [0.1, 0.2, 0.3]
    assert captured["url"] == "http://localhost:11434/api/embeddings"
    assert captured["json"] == {"model": EMBEDDING_MODEL, "prompt": "hello world"}


def test_embed_raises_on_http_error(monkeypatch: pytest.MonkeyPatch):
    def fake_post(url, json, timeout):
        return httpx.Response(500, json={"error": "boom"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", fake_post)

    embedder = OllamaEmbedder(settings=_settings())

    with pytest.raises(httpx.HTTPStatusError):
        embedder.embed("hello")
