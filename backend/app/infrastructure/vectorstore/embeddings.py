"""Local embedding provider — always Ollama's nomic-embed-text, regardless of
LLM_PROVIDER (see docs/design.md). This is the one and only place embeddings
are generated; no second provider abstraction.
"""

import httpx

from app.core.config import Settings, get_settings

EMBEDDING_MODEL = "nomic-embed-text"
EMBEDDING_DIMENSIONS = 768


class OllamaEmbedder:
    def __init__(self, settings: Settings | None = None) -> None:
        self._settings = settings or get_settings()

    def embed(self, text: str) -> list[float]:
        response = httpx.post(
            f"{self._settings.ollama_base_url}/api/embeddings",
            json={"model": EMBEDDING_MODEL, "prompt": text},
            timeout=self._settings.harness_timeout_seconds,
        )
        response.raise_for_status()
        return response.json()["embedding"]
