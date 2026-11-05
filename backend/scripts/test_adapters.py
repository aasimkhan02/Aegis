"""Verification script for Aegis Assistant Adapter System.

Tests all three adapters (Mock, Ollama, HTTP API) with the canonical question:
    "What is the difference between accuracy and reliability?"

Verifies:
- Request acceptance and standardized schema compliance
- Non-empty output
- Latency measurement
- Token usage handling
- Tool call normalization
- Error handling
"""

import asyncio
import os
from pathlib import Path
import sys
from typing import Any
import httpx

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.adapters.exceptions import AdapterConnectionError, AdapterError, AdapterResponseError
from app.adapters.http_api import HttpApiAssistantAdapter
from app.adapters.mock import MockAssistantAdapter
from app.adapters.ollama import OllamaAssistantAdapter
from app.adapters.registry import get_adapter
from app.core.config import settings
from app.schemas.adapter import (
    AssistantResponse,
    ConversationRequest,
    GenerationParameters,
    Message,
    ToolCall,
)

QUESTION = "What is the difference between accuracy and reliability?"


async def test_mock_adapter() -> bool:
    print("\n" + "=" * 60)
    print(" 1. TESTING MOCK ASSISTANT ADAPTER")
    print("=" * 60)

    adapter = get_adapter(
        "mock",
        model="mock-aegis-v1",
        simulated_tool_calls=[
            ToolCall(
                name="calculate_metrics",
                arguments={"metric": "f1_score", "threshold": 0.85},
            )
        ],
    )

    request = ConversationRequest(
        messages=[
            Message(role="system", content="You are a quality testing assistant."),
            Message(role="user", content=QUESTION),
        ],
        parameters=GenerationParameters(temperature=0.0, max_tokens=256),
    )

    passed = True
    try:
        response: AssistantResponse = await adapter.generate(request)
        print(f"[PASS] Request accepted by Mock adapter.")
        print(f"[*] Provider: {response.provider}")
        print(f"[*] Model: {response.model}")
        print(f"[*] Latency: {response.latency_ms} ms")
        print(f"[*] Output (first 120 chars): {response.output[:120]}...")

        # 1. Output non-empty
        if response.output and len(response.output.strip()) > 0:
            print("[PASS] Output is non-empty and well-formed.")
        else:
            print("[FAIL] Output is empty.")
            passed = False

        # 2. Latency measured
        if response.latency_ms >= 0:
            print(f"[PASS] Latency measured: {response.latency_ms} ms.")
        else:
            print("[FAIL] Latency is negative.")
            passed = False

        # 3. Token usage
        if response.token_usage and response.token_usage.total_tokens > 0:
            print(
                f"[PASS] Token usage simulated: prompt={response.token_usage.prompt_tokens}, "
                f"completion={response.token_usage.completion_tokens}, total={response.token_usage.total_tokens}."
            )
        else:
            print("[FAIL] Token usage missing or invalid.")
            passed = False

        # 4. Tool calls
        if len(response.tool_calls) == 1 and response.tool_calls[0].name == "calculate_metrics":
            print(f"[PASS] Tool calls normalized: {response.tool_calls[0].name}({response.tool_calls[0].arguments}).")
        else:
            print("[FAIL] Tool calls normalization failed.")
            passed = False

        # 5. Error handling verification
        error_adapter = MockAssistantAdapter(should_fail=True)
        try:
            await error_adapter.generate(request)
            print("[FAIL] Mock error simulation did not raise AdapterResponseError.")
            passed = False
        except AdapterResponseError as err:
            print(f"[PASS] Mock error handling verified: caught {err.__class__.__name__}: {err.message}")

    except Exception as e:
        print(f"[FAIL] Mock adapter test encountered exception: {e}")
        passed = False

    return passed


async def test_ollama_adapter() -> tuple[bool, bool]:
    """Returns (passed, was_live_tested)."""
    print("\n" + "=" * 60)
    print(" 2. TESTING OLLAMA ASSISTANT ADAPTER")
    print("=" * 60)

    base_url = settings.ollama_base_url
    model = settings.ollama_default_model
    print(f"[*] Ollama Base URL: {base_url}")
    print(f"[*] Ollama Target Model: {model}")

    # Check if Ollama daemon is reachable
    is_reachable = False
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            r = await client.get(f"{base_url.rstrip('/')}/api/tags")
            if r.status_code == 200:
                is_reachable = True
                data = r.json()
                available_models = [m.get("name") for m in data.get("models", [])]
                print(f"[*] Local Ollama is ONLINE. Available models: {available_models}")
        except Exception:
            print("[*] Local Ollama service is not reachable on localhost:11434.")

    adapter = get_adapter("ollama", base_url=base_url, model=model)
    request = ConversationRequest(
        messages=[
            Message(role="system", content="You are an expert on machine learning evaluation."),
            Message(role="user", content=QUESTION),
        ],
        parameters=GenerationParameters(temperature=0.2, max_tokens=150, timeout_seconds=45.0),
    )

    if not is_reachable:
        print("[SKIP] Ollama service not running locally; testing connection error handling.")
        try:
            # Point to an invalid port to verify connection error handling
            bad_adapter = OllamaAssistantAdapter(base_url="http://127.0.0.1:54321")
            await bad_adapter.generate(request)
            print("[FAIL] Ollama unreachable test did not raise AdapterConnectionError.")
            return False, False
        except AdapterConnectionError as exc:
            print(f"[PASS] Connection error correctly caught: {exc.message}")
            return True, False

    # Ollama IS reachable: execute real call
    passed = True
    try:
        print("[*] Sending live query to local Ollama...")
        response: AssistantResponse = await adapter.generate(request)
        print(f"[PASS] Live Ollama response received!")
        print(f"[*] Model: {response.model}")
        print(f"[*] Latency: {response.latency_ms} ms")
        print(f"[*] Output (first 150 chars): {response.output[:150]}...")

        if response.output and len(response.output.strip()) > 0:
            print("[PASS] Ollama output is non-empty.")
        else:
            print("[FAIL] Ollama returned empty output.")
            passed = False

        if response.token_usage:
            print(
                f"[PASS] Ollama token usage extracted: prompt={response.token_usage.prompt_tokens}, "
                f"completion={response.token_usage.completion_tokens}, total={response.token_usage.total_tokens}."
            )
        else:
            print("[*] Ollama did not report token usage (allowed by Ollama when streaming/early abort).")

        print(f"[PASS] Response follows standardized AssistantResponse schema.")
        return passed, True

    except Exception as exc:
        print(f"[FAIL] Ollama invocation failed: {exc}")
        return False, True


async def test_http_api_adapter() -> tuple[bool, bool]:
    """Returns (passed, was_live_tested)."""
    print("\n" + "=" * 60)
    print(" 3. TESTING HTTP API ASSISTANT ADAPTER")
    print("=" * 60)

    api_key = settings.http_adapter_api_key
    base_url = settings.http_adapter_base_url
    model = settings.http_adapter_default_model
    print(f"[*] Base URL: {base_url}")
    print(f"[*] Model: {model}")
    print(f"[*] API Key configured: {'YES (set)' if api_key else 'NO (not set)'}")

    request = ConversationRequest(
        messages=[
            Message(role="system", content="You are a helpful AI assistant."),
            Message(role="user", content=QUESTION),
        ],
        parameters=GenerationParameters(temperature=0.0, max_tokens=150),
    )

    passed = True
    was_live_tested = False

    # 1. First test using mocked HTTP transport to verify full OpenAI spec parsing without paid API
    print("\n--- Subtest A: Mocked HTTP Chat Completions Response Parsing ---")
    mock_payload = {
        "id": "chatcmpl-test-9921",
        "object": "chat.completion",
        "model": "gpt-4o-mini",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": (
                        "Accuracy measures the closeness of agreement between a result and "
                        "the true value. Reliability refers to the repeatability and consistency "
                        "of results across independent evaluations."
                    ),
                    "tool_calls": [
                        {
                            "id": "call_eval_456",
                            "type": "function",
                            "function": {
                                "name": "log_evaluation_metric",
                                "arguments": '{"metric": "accuracy_score", "value": 0.94}',
                            },
                        }
                    ],
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 22,
            "completion_tokens": 36,
            "total_tokens": 58,
        },
    }

    mock_transport = httpx.MockTransport(
        lambda req: httpx.Response(200, json=mock_payload, request=req)
    )
    async with httpx.AsyncClient(transport=mock_transport) as mock_client:
        mock_http_adapter = HttpApiAssistantAdapter(
            base_url="https://api.openai.com/v1",
            api_key="test-mock-key",
            model="gpt-4o-mini",
            client=mock_client,
        )
        try:
            resp = await mock_http_adapter.generate(request)
            print("[PASS] HTTP response successfully parsed by adapter.")
            print(f"[*] Provider: {resp.provider}")
            print(f"[*] Output: {resp.output[:100]}...")
            print(f"[*] Latency: {resp.latency_ms} ms")

            # Check output
            if resp.output:
                print("[PASS] HTTP output is non-empty.")
            else:
                print("[FAIL] HTTP output is empty.")
                passed = False

            # Check token usage
            if resp.token_usage and resp.token_usage.total_tokens == 58:
                print(
                    f"[PASS] Token usage extracted correctly: {resp.token_usage.prompt_tokens} prompt + "
                    f"{resp.token_usage.completion_tokens} completion = {resp.token_usage.total_tokens} total."
                )
            else:
                print("[FAIL] Token usage parsing failed.")
                passed = False

            # Check tool calls
            if len(resp.tool_calls) == 1 and resp.tool_calls[0].name == "log_evaluation_metric":
                print(
                    f"[PASS] Tool calls normalized: {resp.tool_calls[0].name} with args {resp.tool_calls[0].arguments}."
                )
            else:
                print("[FAIL] Tool calls parsing failed.")
                passed = False

        except Exception as exc:
            print(f"[FAIL] Mock HTTP parsing test failed: {exc}")
            passed = False

    # 2. Subtest B: Error response handling (e.g. 401 Unauthorized or 429 Rate Limit)
    print("\n--- Subtest B: HTTP Error Status Handling ---")
    error_payload = {
        "error": {
            "message": "Incorrect API key provided.",
            "type": "invalid_request_error",
            "code": "invalid_api_key",
        }
    }
    err_transport = httpx.MockTransport(
        lambda req: httpx.Response(401, json=error_payload, request=req)
    )
    async with httpx.AsyncClient(transport=err_transport) as err_client:
        err_adapter = HttpApiAssistantAdapter(
            base_url="https://api.openai.com/v1",
            api_key="invalid-key",
            client=err_client,
        )
        try:
            await err_adapter.generate(request)
            print("[FAIL] 401 error response did not raise AdapterResponseError.")
            passed = False
        except AdapterResponseError as err:
            print(f"[PASS] HTTP 401 correctly caught: code={err.status_code}, msg={err.message}")

    # 3. Subtest C: Optional live testing if a real API key is present
    if api_key and not api_key.startswith("change_me"):
        print("\n--- Subtest C: Live HTTP API Call with Configured Key ---")
        live_adapter = get_adapter("http", base_url=base_url, api_key=api_key, model=model)
        try:
            live_resp = await live_adapter.generate(request)
            print(f"[PASS] Live HTTP response received: {live_resp.output[:100]}...")
            was_live_tested = True
        except Exception as exc:
            print(f"[WARN] Live HTTP call failed: {exc}")
    else:
        print("\n[*] Live external API key not configured in environment (skipping paid endpoint call).")

    return passed, was_live_tested


async def main() -> int:
    print("=" * 70)
    print("  AEGIS STEP 3: ASSISTANT ADAPTER SYSTEM VERIFICATION")
    print("=" * 70)
    print(f"Sample Question: {QUESTION!r}")

    mock_ok = await test_mock_adapter()
    ollama_ok, ollama_live = await test_ollama_adapter()
    http_ok, http_live = await test_http_api_adapter()

    print("\n" + "=" * 70)
    print("  VERIFICATION SUMMARY")
    print("=" * 70)
    print(f" - Mock Adapter:       {'PASS' if mock_ok else 'FAIL'}")
    print(f" - Ollama Adapter:     {'PASS' if ollama_ok else 'FAIL'} (Live tested: {'YES' if ollama_live else 'NO'})")
    print(f" - HTTP API Adapter:   {'PASS' if http_ok else 'FAIL'} (Live tested: {'YES' if http_live else 'NO'})")
    print("=" * 70)

    if mock_ok and ollama_ok and http_ok:
        print("[SUCCESS] All adapter requirements and standardized schemas verified!")
        return 0
    else:
        print("[FAILURE] Some adapter tests failed.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))

