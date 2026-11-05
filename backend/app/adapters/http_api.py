"""HTTP API Assistant Adapter supporting OpenAI-compatible Chat Completions endpoints."""

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


class HttpApiAssistantAdapter(BaseAssistantAdapter):
    """Adapter for interacting with OpenAI-compatible HTTP Chat Completions endpoints."""

    provider_name: str = "http"

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        model: str | None = None,
        timeout_seconds: float = 30.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        raw_url = base_url or settings.http_adapter_base_url
        self.base_url = raw_url.rstrip("/")
        # If url already ends with /chat/completions, use as is; otherwise append it
        if self.base_url.endswith("/chat/completions"):
            self.endpoint = self.base_url
        else:
            self.endpoint = f"{self.base_url}/chat/completions"

        self.api_key = api_key if api_key is not None else settings.http_adapter_api_key
        default_model = model or settings.http_adapter_default_model
        super().__init__(model=default_model)
        self.timeout_seconds = timeout_seconds
        self._external_client = client

    async def generate(self, request: ConversationRequest) -> AssistantResponse:
        start_time = time.perf_counter()
        effective_model = request.model or self.model
        prepared_messages = self._prepare_messages(request)

        # Build OpenAI-format messages
        payload_messages = []
        for msg in prepared_messages:
            item: dict[str, Any] = {"role": msg.role, "content": msg.content}
            if msg.name:
                item["name"] = msg.name
            if msg.tool_call_id:
                item["tool_call_id"] = msg.tool_call_id
            if msg.tool_calls:
                item["tool_calls"] = [
                    {
                        "id": tc.id or f"call_{i}",
                        "type": tc.type,
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments)
                            if isinstance(tc.arguments, dict)
                            else str(tc.arguments),
                        },
                    }
                    for i, tc in enumerate(msg.tool_calls)
                ]
            payload_messages.append(item)

        # Build body
        body: dict[str, Any] = {
            "model": effective_model,
            "messages": payload_messages,
        }
        params = request.parameters
        if params.temperature is not None:
            body["temperature"] = params.temperature
        if params.top_p is not None:
            body["top_p"] = params.top_p
        if params.max_tokens is not None:
            body["max_tokens"] = params.max_tokens
        if params.stop is not None:
            body["stop"] = params.stop
        if params.tools:
            body["tools"] = params.tools
        if params.extra:
            body.update(params.extra)

        headers: dict[str, str] = {
            "Content-Type": "application/json",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        timeout = params.timeout_seconds or self.timeout_seconds
        client = self._external_client or httpx.AsyncClient(timeout=timeout)
        should_close = self._external_client is None

        try:
            response = await client.post(self.endpoint, headers=headers, json=body)
        except httpx.TimeoutException as exc:
            raise AdapterConnectionError(
                f"HTTP API request to {self.endpoint} timed out after {timeout}s: {exc}",
                provider=self.provider_name,
            ) from exc
        except httpx.RequestError as exc:
            raise AdapterConnectionError(
                f"Failed to connect to HTTP API at {self.endpoint}: {exc}",
                provider=self.provider_name,
            ) from exc
        finally:
            if should_close:
                await client.aclose()

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        if response.is_error:
            error_details = response.text
            try:
                err_json = response.json()
                if "error" in err_json:
                    error_details = err_json["error"].get("message", error_details)
            except Exception:
                pass
            raise AdapterResponseError(
                f"HTTP API returned status {response.status_code}: {error_details}",
                provider=self.provider_name,
                status_code=response.status_code,
                details=error_details,
            )

        try:
            data = response.json()
        except Exception as exc:
            raise AdapterResponseError(
                f"HTTP API returned malformed JSON response: {exc}",
                provider=self.provider_name,
                status_code=response.status_code,
                details=response.text,
            ) from exc

        choices = data.get("choices", [])
        if not choices:
            raise AdapterResponseError(
                "HTTP API returned empty 'choices' list in response",
                provider=self.provider_name,
                status_code=response.status_code,
                details=data,
            )

        first_choice = choices[0]
        choice_message = first_choice.get("message", {})
        output = choice_message.get("content") or ""

        # Extract and normalize tool calls
        raw_tool_calls = choice_message.get("tool_calls", [])
        tool_calls: list[ToolCall] = []
        for raw_tc in raw_tool_calls:
            tc_id = raw_tc.get("id")
            fn = raw_tc.get("function", {})
            name = fn.get("name", "unknown")
            raw_args = fn.get("arguments", {})
            parsed_args: dict[str, Any] | str
            if isinstance(raw_args, str):
                try:
                    parsed_args = json.loads(raw_args)
                except Exception:
                    parsed_args = raw_args
            else:
                parsed_args = raw_args

            tool_calls.append(
                ToolCall(
                    id=tc_id,
                    name=name,
                    arguments=parsed_args,
                    type=raw_tc.get("type", "function"),
                )
            )

        # Extract token usage
        usage_data = data.get("usage")
        token_usage: TokenUsage | None = None
        if usage_data:
            token_usage = TokenUsage(
                prompt_tokens=usage_data.get("prompt_tokens", 0),
                completion_tokens=usage_data.get("completion_tokens", 0),
                total_tokens=usage_data.get("total_tokens", 0),
            )

        metadata: dict[str, Any] = {
            "id": data.get("id"),
            "finish_reason": first_choice.get("finish_reason"),
            "response_model": data.get("model", effective_model),
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

