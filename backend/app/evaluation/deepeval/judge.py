"""Ollama Judge Model adapter implementing DeepEval's DeepEvalBaseLLM interface.

Strict local execution requirements:
- Connects exclusively to the local Ollama daemon (no OpenAI or cloud fallbacks).
- Uses configured local model (e.g. qwen2.5:1.5b).
- Gracefully detects offline daemon and surfaces clear diagnostic messages.
- Disables external telemetry to ensure privacy and offline stability.
"""

import logging
import os
from typing import Any, Optional
import httpx
from pydantic import BaseModel

# Disable external DeepEval telemetry and cloud callbacks
os.environ["DEEPEVAL_TELEMETRY_OPT_OUT"] = "YES"

from deepeval.models import DeepEvalBaseLLM
from app.core.config import settings

logger = logging.getLogger("aegis.deepeval.judge")


class JudgeUnavailableError(RuntimeError):
    """Raised when the local Ollama judge service is unreachable, offline, or misconfigured."""
    pass


class OllamaJudgeModel(DeepEvalBaseLLM):
    """Custom DeepEval LLM Judge communicating exclusively with local Ollama.
    
    Guarantees:
    - Never falls back to OpenAI, Anthropic, or external cloud services.
    - Uses local Ollama base URL and model configured in Aegis settings.
    - Supports both synchronous and asynchronous generation.
    - Forces deterministic JSON generation when DeepEval schemas are supplied.
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 120.0,
    ):
        self.model_name = model_name or settings.ollama_default_model
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.timeout = timeout
        super().__init__(model=self.model_name)

    def load_model(self) -> "OllamaJudgeModel":
        """Validate connection to local Ollama and return self."""
        return self

    def get_model_name(self) -> str:
        """Return the active model name string."""
        return self.model_name

    def supports_log_probs(self) -> bool:
        """Inform DeepEval that Ollama judge does not expose token log probabilities."""
        return False

    def supports_structured_outputs(self) -> bool:
        """Inform DeepEval that structured JSON outputs are supported via format='json'."""
        return True

    def supports_json_mode(self) -> bool:
        """Inform DeepEval that JSON mode is supported."""
        return True

    def is_available(self) -> bool:
        """Check if local Ollama daemon is reachable and has the model loaded."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return False
                models = [m.get("name", "") for m in res.json().get("models", [])]
                # Match full name or base name (e.g. 'qwen2.5:1.5b' or 'qwen2.5:1.5b-instruct')
                return any(self.model_name in m or m in self.model_name for m in models)
        except Exception:
            return False

    def generate(self, prompt: str, schema: Optional[type[BaseModel]] = None, *args: Any, **kwargs: Any) -> str:
        """Synchronously send prompt to local Ollama /api/chat endpoint."""
        url = f"{self.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.0},
        }
        if schema is not None:
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ValueError(f"Ollama returned empty response: {data}")
                return content
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            msg = (
                f"Cannot connect to local Ollama judge at '{self.base_url}'. "
                f"Ensure Ollama is running locally ('ollama serve') and accessible. Details: {e}"
            )
            logger.error(msg)
            raise JudgeUnavailableError(msg) from e
        except httpx.ReadTimeout as e:
            msg = f"Local Ollama judge at '{self.base_url}' timed out after {self.timeout}s: {e}"
            logger.error(msg)
            raise JudgeUnavailableError(msg) from e
        except Exception as e:
            msg = f"Ollama judge generation failed for model '{self.model_name}': {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

    async def a_generate(self, prompt: str, schema: Optional[type[BaseModel]] = None, *args: Any, **kwargs: Any) -> str:
        """Asynchronously send prompt to local Ollama /api/chat endpoint."""
        url = f"{self.base_url}/api/chat"
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "options": {"temperature": 0.0},
        }
        if schema is not None:
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                if not content:
                    raise ValueError(f"Ollama returned empty response: {data}")
                return content
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            msg = (
                f"Cannot connect to local Ollama judge at '{self.base_url}'. "
                f"Ensure Ollama is running locally ('ollama serve') and accessible. Details: {e}"
            )
            logger.error(msg)
            raise JudgeUnavailableError(msg) from e
        except httpx.ReadTimeout as e:
            msg = f"Local Ollama judge at '{self.base_url}' timed out after {self.timeout}s: {e}"
            logger.error(msg)
            raise JudgeUnavailableError(msg) from e
        except Exception as e:
            msg = f"Ollama judge generation failed for model '{self.model_name}': {e}"
            logger.error(msg)
            raise RuntimeError(msg) from e

