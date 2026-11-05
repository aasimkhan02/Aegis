"""Mock Assistant Adapter for offline testing and deterministic evaluation."""

import asyncio
import time
from typing import Any

from app.adapters.base import BaseAssistantAdapter
from app.adapters.exceptions import AdapterResponseError
from app.schemas.adapter import (
    AssistantResponse,
    ConversationRequest,
    TokenUsage,
    ToolCall,
)


class MockAssistantAdapter(BaseAssistantAdapter):
    """Deterministic, zero-dependency mock adapter for testing."""

    provider_name: str = "mock"

    def __init__(
        self,
        model: str = "mock-gpt-v1",
        default_response: str | None = None,
        custom_responses: dict[str, str] | None = None,
        simulated_latency_ms: int = 10,
        simulated_tool_calls: list[ToolCall] | None = None,
        should_fail: bool = False,
    ) -> None:
        super().__init__(model=model)
        self.default_response = default_response
        self.custom_responses = custom_responses or {}
        self.simulated_latency_ms = simulated_latency_ms
        self.simulated_tool_calls = simulated_tool_calls or []
        self.should_fail = should_fail

    async def generate(self, request: ConversationRequest) -> AssistantResponse:
        start_time = time.perf_counter()

        # Simulate brief latency
        if self.simulated_latency_ms > 0:
            await asyncio.sleep(self.simulated_latency_ms / 1000.0)

        if self.should_fail:
            raise AdapterResponseError(
                message="Simulated mock provider failure",
                provider=self.provider_name,
                status_code=500,
            )

        messages = self._prepare_messages(request)
        last_user_msg = ""
        for msg in reversed(messages):
            if msg.role == "user":
                last_user_msg = msg.content
                break

        # Check custom responses first
        if last_user_msg in self.custom_responses:
            output = self.custom_responses[last_user_msg]
        elif self.default_response is not None:
            output = self.default_response
        elif "accuracy" in last_user_msg.lower() and "reliability" in last_user_msg.lower():
            output = (
                "Accuracy refers to how close a measurement or model prediction is to the "
                "true or accepted standard value. Reliability (consistency or precision) "
                "refers to the degree to which an assessment tool or model produces stable "
                "and consistent results across repeated trials. A system can be reliable "
                "without being accurate (consistently wrong), but high-quality AI systems "
                "require both high accuracy and high reliability."
            )
        elif last_user_msg:
            output = f"Mock response to: {last_user_msg}"
        else:
            output = "Mock assistant response (empty prompt)."

        # Simulate realistic token counts (approx ~1.3 tokens per word)
        total_prompt_words = sum(len(m.content.split()) for m in messages)
        prompt_tokens = max(1, int(total_prompt_words * 1.3))
        completion_tokens = max(1, int(len(output.split()) * 1.3))
        token_usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )

        latency_ms = int((time.perf_counter() - start_time) * 1000)

        effective_model = request.model or self.model

        return AssistantResponse(
            output=output,
            provider=self.provider_name,
            model=effective_model,
            latency_ms=latency_ms,
            token_usage=token_usage,
            tool_calls=list(self.simulated_tool_calls),
            metadata={
                "finish_reason": "stop",
                "simulated": True,
                "messages_count": len(messages),
            },
        )

