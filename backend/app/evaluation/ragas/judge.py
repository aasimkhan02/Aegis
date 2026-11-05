"""Custom Ollama judge model interface for Ragas evaluations."""

import json
import logging
from typing import Any, Optional
import httpx
from langchain_core.outputs import Generation, LLMResult
from langchain_core.prompt_values import PromptValue
from ragas.llms.base import BaseRagasLLM
from ragas.run_config import RunConfig

from app.core.config import settings

logger = logging.getLogger("aegis.evaluation.ragas.judge")


class RagasJudgeUnavailableError(RuntimeError):
    """Raised when the local Ollama judge model daemon is offline, timed out, or returning HTTP errors."""
    pass


class RagasOllamaJudgeModel(BaseRagasLLM):
    """Custom Ragas LLM adapter communicating directly with local Ollama daemon.
    
    Adheres to Ragas 0.2.x BaseRagasLLM interface using httpx with configurable timeouts.
    """

    base_url: str
    model_name: str
    timeout_seconds: float
    temperature: float

    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        temperature: float = 1e-8,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model_name = model_name or settings.ollama_default_model
        self.timeout_seconds = timeout_seconds or getattr(settings, "ollama_timeout_seconds", 120.0)
        self.temperature = temperature
        self.last_responses: list[str] = []
        self._response_cache: dict[tuple[str, float], str] = {}
        self.set_run_config(RunConfig(timeout=int(self.timeout_seconds), max_retries=1, max_wait=2))

    def get_model_name(self) -> str:
        return self.model_name

    def is_available(self) -> bool:
        """Check whether the configured Ollama daemon is reachable and the model exists."""
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return False
                models = [m.get("name", "") for m in res.json().get("models", [])]
                return any(self.model_name in m for m in models)
        except Exception as e:
            logger.debug("Ragas Ollama availability check failed: %s", e)
            return False

    def is_finished(self, response: LLMResult) -> bool:
        """Indicate completion to prevent Ragas BaseRagasLLM unimplemented warnings."""
        return True

    def generate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
        callbacks: Any = None,
    ) -> LLMResult:
        """Synchronously generate text using local Ollama /api/generate."""
        prompt_text = prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)
        temp = temperature if temperature is not None else self.temperature
        cache_key = (prompt_text, float(temp))
        if cache_key in self._response_cache:
            output_text = self._response_cache[cache_key]
            self.last_responses.append(output_text)
            return LLMResult(generations=[[Generation(text=output_text)]])

        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt_text,
            "stream": False,
            "options": {
                "temperature": temp,
            },
        }

        # Ollama supports constrained JSON formatting if JSON is requested
        if "json" in prompt_text.lower():
            payload["format"] = "json"

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                if response.status_code != 200:
                    raise RagasJudgeUnavailableError(
                        f"Ollama returned HTTP {response.status_code}: {response.text}"
                    )
                data = response.json()
                output_text = data.get("response", "")
                self.last_responses.append(output_text)
                self._cache_response(cache_key, output_text)
                return LLMResult(generations=[[Generation(text=output_text)]])
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise RagasJudgeUnavailableError(
                f"Connection refused: Ollama daemon offline at {self.base_url} ({e})"
            ) from e
        except httpx.ReadTimeout as e:
            raise RagasJudgeUnavailableError(
                f"Local Ollama judge timed out after {self.timeout_seconds}s ({e})"
            ) from e
        except Exception as e:
            if isinstance(e, RagasJudgeUnavailableError):
                raise
            raise RagasJudgeUnavailableError(f"Ollama execution failed: {e}") from e

    async def agenerate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
        callbacks: Any = None,
    ) -> LLMResult:
        """Asynchronously generate text using local Ollama /api/generate."""
        prompt_text = prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)
        temp = temperature if temperature is not None else self.temperature
        cache_key = (prompt_text, float(temp))
        if cache_key in self._response_cache:
            output_text = self._response_cache[cache_key]
            self.last_responses.append(output_text)
            return LLMResult(generations=[[Generation(text=output_text)]])

        payload: dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt_text,
            "stream": False,
            "options": {
                "temperature": temp,
            },
        }

        if "json" in prompt_text.lower():
            payload["format"] = "json"

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json=payload,
                )
                if response.status_code != 200:
                    raise RagasJudgeUnavailableError(
                        f"Ollama returned HTTP {response.status_code}: {response.text}"
                    )
                data = response.json()
                output_text = data.get("response", "")
                self.last_responses.append(output_text)
                self._cache_response(cache_key, output_text)
                return LLMResult(generations=[[Generation(text=output_text)]])
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            raise RagasJudgeUnavailableError(
                f"Connection refused: Ollama daemon offline at {self.base_url} ({e})"
            ) from e
        except httpx.ReadTimeout as e:
            raise RagasJudgeUnavailableError(
                f"Local Ollama judge timed out after {self.timeout_seconds}s ({e})"
            ) from e
        except Exception as e:
            if isinstance(e, RagasJudgeUnavailableError):
                raise
            raise RagasJudgeUnavailableError(f"Ollama execution failed: {e}") from e

    def _cache_response(self, key: tuple[str, float], response: str) -> None:
        """Keep a small per-instance cache for exact repeat prompts only."""
        if len(self._response_cache) >= 128:
            self._response_cache.pop(next(iter(self._response_cache)))
        self._response_cache[key] = response


class MockRagasJudgeModel(BaseRagasLLM):
    """Fast, deterministic mock judge model for automated unit tests without network access."""

    def __init__(
        self,
        model_name: str = "mock-ragas-judge",
        should_fail: bool = False,
        timeout_fail: bool = False,
        malformed: bool = False,
        mock_statements: Optional[list[str]] = None,
        faithfulness_verdict: int = 1,
        precision_verdict: int = 1,
        recall_attributed: int = 1,
        *args: Any,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self.model_name = model_name
        self.should_fail = should_fail
        self.timeout_fail = timeout_fail
        self.malformed = malformed
        self.mock_statements = mock_statements or ["The fan includes a 2-year warranty."]
        self.faithfulness_verdict = faithfulness_verdict
        self.precision_verdict = precision_verdict
        self.recall_attributed = recall_attributed
        self.last_responses: list[str] = []
        self.set_run_config(RunConfig(timeout=2, max_retries=0, max_wait=0))

    def get_model_name(self) -> str:
        return self.model_name

    def is_finished(self, response: LLMResult) -> bool:
        return True

    def generate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
        callbacks: Any = None,
    ) -> LLMResult:
        if self.should_fail:
            raise RagasJudgeUnavailableError("Mocked connection refused: Ollama daemon is offline.")
        if self.timeout_fail:
            raise RagasJudgeUnavailableError("Mocked timeout: Local Ollama judge timed out after 120s.")
        if self.malformed:
            output = "This is not valid JSON {{{"
            self.last_responses.append(output)
            return LLMResult(generations=[[Generation(text=output)]])

        text = (prompt.to_string() if hasattr(prompt, "to_string") else str(prompt)).lower()

        # Route response according to Ragas prompt instructions
        if "analyze the complexity" in text or "statements" in text and "complexity" in text:
            out = json.dumps({"statements": self.mock_statements})
        elif "natural language inference" in text or ("verdict" in text and "statement" in text):
            out = json.dumps({
                "statements": [
                    {
                        "statement": s,
                        "verdict": self.faithfulness_verdict,
                        "reason": "Mocked NLI reason.",
                    }
                    for s in self.mock_statements
                ]
            })
        elif "context_precision" in text or "relevance" in text or "given a question, context" in text:
            out = json.dumps({
                "verdict": self.precision_verdict,
                "reason": "Mocked context precision relevance verdict.",
            })
        elif "recall" in text or "attributed" in text or "classification" in text:
            out = json.dumps({
                "classifications": [
                    {
                        "statement": s,
                        "attributed": self.recall_attributed,
                        "reason": "Mocked context recall attribution.",
                    }
                    for s in self.mock_statements
                ]
            })
        else:
            out = json.dumps({"verdict": 1, "reason": "Default mock response."})

        self.last_responses.append(out)
        return LLMResult(generations=[[Generation(text=out)]])

    async def agenerate_text(
        self,
        prompt: PromptValue,
        n: int = 1,
        temperature: Optional[float] = None,
        stop: Optional[list[str]] = None,
        callbacks: Any = None,
    ) -> LLMResult:
        return self.generate_text(prompt, n, temperature, stop, callbacks)
