"""Ollama Assistant Adapter communicating with local Ollama daemon."""

import json
import time
from typing import Any
import httpx

from app.adapters.base import BaseAssistantAdapter
from app.adapters.exceptions import (
    AdapterConnectionError,
    AdapterResponseError,
)
from app.core.config import settings
from app.schemas.adapter import (
    AssistantResponse,
    ConversationRequest,
    TokenUsage,
    ToolCall,
)


class OllamaAssistantAdapter(BaseAssistantAdapter):
    """Adapter for interacting with local Ollama chat completions API."""

    provider_name: str = "ollama"

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 60.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        raw_url = base_url or settings.ollama_base_url
        self.base_url = raw_url.rstrip("/")
        default_model = model or settings.ollama_default_model
        super().__init__(model=default_model)
        self.timeout_seconds = timeout_seconds
        self._external_client = client

    async def generate(self, request: ConversationRequest) -> AssistantResponse:
        start_time = time.perf_counter()
        effective_model = request.model or self.model
        prepared_messages = self._prepare_messages(request)

        # Build Ollama message payload
        payload_messages = []
        for msg in prepared_messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "function": {
                            "name": tc.name,
                            "arguments": tc.arguments
                            if isinstance(tc.arguments, dict)
                            else {},
                        }
                    }
                    for tc in msg.tool_calls
                ]
            payload_messages.append(item)

        # Build options dictionary
        options: dict[str, Any] = {}
        params = request.parameters
        if params.temperature is not None:
            options["temperature"] = params.temperature
        if params.top_p is not None:
            options["top_p"] = params.top_p
        if params.max_tokens is not None:
            options["num_predict"] = params.max_tokens
        if params.stop is not None:
            options["stop"] = (
                params.stop if isinstance(params.stop, list) else [params.stop]
            )
        if params.extra:
            options.update(params.extra)

        body: dict[str, Any] = {
            "model": effective_model,
            "messages": payload_messages,
            "stream": False,
        }
        if options:
            body["options"] = options
        if params.tools:
            body["tools"] = params.tools

        endpoint = f"{self.base_url}/api/chat"
        timeout = params.timeout_seconds or self.timeout_seconds

        client = self._external_client or httpx.AsyncClient(timeout=timeout)
        should_close = self._external_client is None

        try:
            response = await client.post(endpoint, json=body)
        except httpx.TimeoutException as exc:
            raise AdapterConnectionError(
                f"Ollama request timed out after {timeout}s: {exc}",
                provider=self.provider_name,
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterConnectionError(
                f"Failed to connect to Ollama at {endpoint}: {exc}",
                provider=self.provider_name,
            ) from exc
        finally:
            if should_close:
                await client.aclose()

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if response.is_error:
            error_text = response.text
            try:
                err_json = response.json()
                error_text = err_json.get("error", error_text)
            except Exception:
                pass
            raise AdapterResponseError(
                f"Ollama returned HTTP {response.status_code}: {error_text}",
                provider=self.provider_name,
                status_code=response.status_code,
                details=error_text,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AdapterResponseError(
                f"Ollama returned invalid JSON: {exc}",
                provider=self.provider_name,
                status_code=response.status_code,
                details=response.text,
            ) from exc

        # Extract output text
        msg_obj = data.get("message", {})
        output = msg_obj.get("content", "")

        # Extract & normalize tool calls
        raw_tool_calls = msg_obj.get("tool_calls", [])
        tool_calls: list[ToolCall] = []
        for raw_tc in raw_tool_calls:
            fn = raw_tc.get("function", {})
            name = fn.get("name", "unknown")
            args = fn.get("arguments", {})
            tool_calls.append(
                ToolCall(
                    name=name,
                    arguments=args,
                    type="function",
                )
            )

        # Extract token usage if reported by Ollama
        prompt_eval_count = data.get("prompt_eval_count")
        eval_count = data.get("eval_count")
        token_usage: TokenUsage | None = None
        if prompt_eval_count is not None and eval_count is not None:
            token_usage = TokenUsage(
                prompt_tokens=prompt_eval_count,
                completion_tokens=eval_count,
                total_tokens=prompt_eval_count + eval_count,
            )

        metadata: dict[str, Any] = {
            "done": data.get("done", True),
            "done_reason": data.get("done_reason"),
            "total_duration_ns": data.get("total_duration"),
            "load_duration_ns": data.get("load_duration"),
        }

        return AssistantResponse(
            output=output,
            provider=self.provider_name,
            model=data.get("model", effective_model),
            latency_ms=latency_ms,
            token_usage=token_usage,
            tool_calls=tool_calls,
            metadata=metadata,
        )

