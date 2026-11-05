"""Local Ollama embeddings interface for Ragas."""

import logging
from typing import Any, List, Optional
import httpx
from ragas.embeddings.base import BaseRagasEmbeddings

from app.core.config import settings

logger = logging.getLogger("aegis.evaluation.ragas.embeddings")


class RagasEmbeddingUnavailableError(RuntimeError):
    """Raised when an embedding provider or local embedding model is unavailable."""
    pass


class RagasOllamaEmbeddings(BaseRagasEmbeddings):
    """Lightweight local Ollama embeddings adapter for Ragas.
    
    Checks if a local embedding model is installed in Ollama (e.g., 'nomic-embed-text' or 'all-minilm')
    without downloading large models or calling external paid cloud APIs.
    """

    base_url: str
    model_name: str
    timeout_seconds: float

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: str = "nomic-embed-text",
        timeout_seconds: float = 30.0,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        """Verify whether the embedding model is available on the local Ollama daemon."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return False
                models = [m.get("name", "") for m in res.json().get("models", [])]
                return any(self.model_name in m for m in models)
        except Exception as e:
            logger.debug("Ollama embedding model check failed: %s", e)
            return False

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        if not self.is_available():
            raise RagasEmbeddingUnavailableError(
                f"Local Ollama embedding model '{self.model_name}' is not installed at {self.base_url}. "
                f"Run `ollama pull {self.model_name}` to enable local embeddings."
            )
        try:
            results: List[List[float]] = []
            with httpx.Client(timeout=self.timeout_seconds) as client:
                for text in texts:
                    res = client.post(
                        f"{self.base_url}/api/embeddings",
                        json={"model": self.model_name, "prompt": text},
                    )
                    if res.status_code != 200:
                        raise RagasEmbeddingUnavailableError(
                            f"Ollama embedding API error (HTTP {res.status_code}): {res.text}"
                        )
                    results.append(res.json().get("embedding", []))
            return results
        except Exception as e:
            if isinstance(e, RagasEmbeddingUnavailableError):
                raise
            raise RagasEmbeddingUnavailableError(f"Embedding generation failed: {e}") from e

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return self.embed_query(text)


class MockRagasEmbeddings(BaseRagasEmbeddings):
    """Deterministic mock embedding provider for testing."""

    def __init__(self, dimension: int = 4, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.dimension = dimension

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [[float(i + 1) / 10.0 for i in range(self.dimension)] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        return [float(i + 1) / 10.0 for i in range(self.dimension)]

    async def aembed_documents(self, texts: List[str]) -> List[List[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> List[float]:
        return self.embed_query(text)

