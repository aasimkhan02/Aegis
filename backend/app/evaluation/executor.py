"""Executor for single test cases and assistant adapter resolution."""

from dataclasses import dataclass, field
import time
from typing import Any, Union
import uuid

from app.adapters.base import BaseAssistantAdapter
from app.adapters.registry import get_adapter
from app.demo.orchestrator import DemoAssistantOrchestrator
from app.evaluation.context import EvaluationContext, TestCaseData
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult
from app.evaluation.exceptions import AssistantResolutionError
from app.models.assistant_version import AssistantVersion
from app.models.test_case import TestCase
from app.schemas.adapter import (
    AssistantResponse,
    ConversationRequest,
    GenerationParameters,
    Message,
)


@dataclass
class TestCaseExecutionResult:
    """Outcome of executing a single test case through the adapter and evaluators."""

    test_case_id: uuid.UUID
    test_case_snapshot: dict[str, Any]
    actual_output: dict[str, Any] | None
    status: str  # 'passed', 'failed', 'error', 'skipped'
    error_message: str | None
    latency_ms: int
    metric_results: list[EvaluatorResult] = field(default_factory=list)


def resolve_assistant_adapter(assistant_version: AssistantVersion) -> BaseAssistantAdapter:
    """Instantiate the appropriate assistant adapter matching the persisted AssistantVersion.

    Supports:
    1. BharatHome Assistant v1 (Production / Good)
    2. BharatHome Assistant v2 (Intentionally Broken)
    3. Generic Mock adapter
    4. Ollama adapter
    5. HTTP API adapter
    """
    version_str = (assistant_version.version or "").lower()
    name_str = (assistant_version.name or "").lower()
    model_str = (assistant_version.model_name or "").lower()
    provider_str = (assistant_version.provider or "mock").lower().strip()
    config = assistant_version.config or {}

    # Check for BharatHome Demo Assistant configurations
    is_v1 = "v1" in version_str or "v1" in name_str or "good" in version_str or "bharathome-v1" in model_str
    is_v2 = "v2" in version_str or "v2" in name_str or "broken" in version_str or "bharathome-v2" in model_str

    if is_v1 or is_v2:
        version_flag = "v1" if is_v1 else "v2"
        base_url = config.get("base_url")
        api_key = config.get("api_key")
        return DemoAssistantOrchestrator(
            assistant_version=version_flag,
            provider=provider_str,
            base_url=base_url,
            model=assistant_version.model_name,
            api_key=api_key,
        )

    # Standard adapter resolution via adapter registry
    try:
        return get_adapter(
            provider=provider_str,
            base_url=config.get("base_url"),
            model=assistant_version.model_name,
            api_key=config.get("api_key"),
            **{k: v for k, v in config.items() if k not in ("base_url", "api_key")},
        )
    except Exception as e:
        raise AssistantResolutionError(
            f"Failed to resolve assistant provider '{provider_str}' for version '{assistant_version.version}': {e}"
        ) from e


def build_conversation_request(
    test_case: Union[TestCase, TestCaseData],
    system_prompt: str | None = None,
) -> ConversationRequest:
    """Convert a TestCase's input_data and retrieval_context into a standardized ConversationRequest."""
    input_data = test_case.input_data or {}
    messages: list[Message] = []

    # Case 1: input_data contains structured messages list
    if "messages" in input_data and isinstance(input_data["messages"], list):
        for m in input_data["messages"]:
            if isinstance(m, dict) and "role" in m and "content" in m:
                messages.append(Message(role=m["role"], content=str(m["content"])))
            elif isinstance(m, str):
                messages.append(Message(role="user", content=m))

    # Case 2: input_data contains simple text query/prompt/input
    elif any(k in input_data for k in ("query", "prompt", "input", "text")):
        for k in ("query", "prompt", "input", "text"):
            if k in input_data and input_data[k]:
                messages.append(Message(role="user", content=str(input_data[k])))
                break

    # Case 3: input_data is a dictionary of fields (e.g. customer_name, issue)
    elif input_data:
        summary_parts = [f"{k}: {v}" for k, v in input_data.items() if v]
        messages.append(Message(role="user", content=", ".join(summary_parts)))

    # Fallback: empty prompt
    if not messages:
        messages.append(Message(role="user", content=test_case.name))

    # Incorporate retrieval context if present
    parameters = GenerationParameters()
    if test_case.retrieval_context:
        parameters.extra["retrieval_context"] = test_case.retrieval_context

    return ConversationRequest(
        messages=messages,
        system_prompt=system_prompt,
        parameters=parameters,
    )


def create_test_case_snapshot(test_case: Union[TestCase, TestCaseData]) -> dict[str, Any]:
    """Capture an immutable snapshot of a TestCase to preserve historical integrity."""
    if isinstance(test_case, TestCaseData):
        return test_case.to_snapshot()

    return {
        "id": str(test_case.id),
        "name": test_case.name,
        "input_data": test_case.input_data or {},
        "expected_output": test_case.expected_output,
        "expected_behavior": test_case.expected_behavior,
        "retrieval_context": test_case.retrieval_context,
        "ground_truth_context": getattr(test_case, "ground_truth_context", None),
        "tags": test_case.tags if isinstance(test_case.tags, list) else [],
        "metadata": getattr(test_case, "metadata_", {}) or {},
        "is_enabled": test_case.is_enabled,
    }


async def execute_test_case(
    test_case: Union[TestCase, TestCaseData],
    adapter: BaseAssistantAdapter,
    evaluators: list[BaseEvaluator],
    system_prompt: str | None = None,
) -> TestCaseExecutionResult:
    """Execute a single test case through the assistant adapter and evaluate metrics."""
    snapshot = create_test_case_snapshot(test_case)
    start_time = time.perf_counter()

    actual_response: AssistantResponse | None = None
    error_message: str | None = None
    latency_ms = 0

    try:
        request = build_conversation_request(test_case, system_prompt=system_prompt)
        actual_response = await adapter.generate(request)
        latency_ms = actual_response.latency_ms if actual_response.latency_ms > 0 else int((time.perf_counter() - start_time) * 1000)
    except Exception as e:
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        error_message = f"Assistant execution failed: {type(e).__name__}: {e}"

    # Package response payload for persistence
    actual_output_dict: dict[str, Any] | None = None
    if actual_response is not None:
        actual_output_dict = {
            "output": actual_response.output,
            "provider": actual_response.provider,
            "model": actual_response.model,
            "latency_ms": latency_ms,
            "token_usage": actual_response.token_usage.model_dump() if actual_response.token_usage else None,
            "tool_calls": [tc.model_dump() for tc in actual_response.tool_calls],
            "metadata": actual_response.metadata,
        }

    # Build evaluation context
    context = EvaluationContext(
        test_case_id=test_case.id,
        test_case_name=test_case.name,
        input_data=test_case.input_data or {},
        expected_output=test_case.expected_output,
        expected_behavior=test_case.expected_behavior,
        retrieval_context=test_case.retrieval_context,
        ground_truth_context=getattr(test_case, "ground_truth_context", None),
        tags=snapshot.get("tags", []),
        metadata=snapshot.get("metadata", {}),
        actual_response=actual_response,
        error_message=error_message,
        latency_ms=latency_ms,
    )

    # Compute metrics with evaluators
    metric_results: list[EvaluatorResult] = []
    case_status = "error" if error_message is not None else "passed"

    for evaluator in evaluators:
        try:
            res = evaluator.evaluate(context)
            metric_results.append(res)
            # Only genuine applicable and mandatory metric failures fail the test case
            if res.applicable and res.mandatory and not res.passed and case_status != "error":
                case_status = "failed"
        except Exception as e:
            # Evaluator infrastructure errors must NOT degrade assistant pass rates
            metric_results.append(
                EvaluatorResult(
                    metric_name=evaluator.name,
                    score=0.0,
                    threshold=evaluator.default_threshold,
                    passed=False,
                    applicable=False,
                    mandatory=False,
                    details={
                        "status": "evaluator_error",
                        "evaluator_error": True,
                        "error_type": type(e).__name__,
                        "error": f"Evaluator execution exception: {e}",
                        "applicable": False,
                    },
                )
            )

    return TestCaseExecutionResult(
        test_case_id=test_case.id,
        test_case_snapshot=snapshot,
        actual_output=actual_output_dict,
        status=case_status,
        error_message=error_message,
        latency_ms=latency_ms,
        metric_results=metric_results,
    )
