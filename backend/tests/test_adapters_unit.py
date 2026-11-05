"""Unit tests for the Aegis Assistant Adapter System."""

import asyncio
import json
from pathlib import Path
import sys
import unittest
import httpx

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.adapters.base import BaseAssistantAdapter
from app.adapters.exceptions import (
    AdapterConfigError,
    AdapterConnectionError,
    AdapterResponseError,
)
from app.adapters.http_api import HttpApiAssistantAdapter
from app.adapters.mock import MockAssistantAdapter
from app.adapters.ollama import OllamaAssistantAdapter
from app.adapters.registry import get_adapter, register_adapter
from app.schemas.adapter import (
    AssistantResponse,
    ConversationRequest,
    GenerationParameters,
    Message,
    ToolCall,
)


class TestMockAdapter(unittest.IsolatedAsyncioTestCase):
    async def test_mock_deterministic_generation(self):
        adapter = MockAssistantAdapter(model="mock-model")
        req = ConversationRequest(
            messages=[
                Message(role="user", content="What is the difference between accuracy and reliability?")
            ]
        )
        res = await adapter.generate(req)
        self.assertIsInstance(res, AssistantResponse)
        self.assertEqual(res.provider, "mock")
        self.assertEqual(res.model, "mock-model")
        self.assertIn("Accuracy", res.output)
        self.assertIn("reliability", res.output.lower())
        self.assertGreater(res.latency_ms, 0)
        self.assertIsNotNone(res.token_usage)
        self.assertGreater(res.token_usage.total_tokens, 0)

    async def test_mock_custom_responses(self):
        adapter = MockAssistantAdapter(
            custom_responses={"Hello": "Hi there, tester!"}
        )
        req = ConversationRequest(messages=[Message(role="user", content="Hello")])
        res = await adapter.generate(req)
        self.assertEqual(res.output, "Hi there, tester!")

    async def test_mock_simulated_tool_calls(self):
        tc = ToolCall(name="evaluate_prompt", arguments={"metric": "safety"})
        adapter = MockAssistantAdapter(simulated_tool_calls=[tc])
        req = ConversationRequest(messages=[Message(role="user", content="Test prompt")])
        res = await adapter.generate(req)
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0].name, "evaluate_prompt")
        self.assertEqual(res.tool_calls[0].arguments, {"metric": "safety"})

    async def test_mock_error_handling(self):
        adapter = MockAssistantAdapter(should_fail=True)
        req = ConversationRequest(messages=[Message(role="user", content="Test")])
        with self.assertRaises(AdapterResponseError) as ctx:
            await adapter.generate(req)
        self.assertEqual(ctx.exception.status_code, 500)


class TestOllamaAdapter(unittest.IsolatedAsyncioTestCase):
    async def test_ollama_success_response_parsing(self):
        mock_response_data = {
            "model": "qwen2.5:1.5b",
            "message": {
                "role": "assistant",
                "content": "Accuracy is closeness to ground truth; reliability is consistency.",
                "tool_calls": [
                    {
                        "function": {
                            "name": "lookup_benchmark",
                            "arguments": {"suite": "ragas"},
                        }
                    }
                ],
            },
            "done": True,
            "total_duration": 4500000000,
            "prompt_eval_count": 28,
            "eval_count": 42,
        }

        transport = httpx.MockTransport(
            lambda req: httpx.Response(200, json=mock_response_data, request=req)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = OllamaAssistantAdapter(
                base_url="http://localhost:11434",
                model="qwen2.5:1.5b",
                client=client,
            )
            req = ConversationRequest(
                system_prompt="Be concise.",
                messages=[
                    Message(role="user", content="Explain accuracy vs reliability")
                ],
                parameters=GenerationParameters(temperature=0.5, max_tokens=100),
            )
            res = await adapter.generate(req)

            self.assertEqual(res.provider, "ollama")
            self.assertEqual(res.model, "qwen2.5:1.5b")
            self.assertEqual(res.output, "Accuracy is closeness to ground truth; reliability is consistency.")
            self.assertIsNotNone(res.token_usage)
            self.assertEqual(res.token_usage.prompt_tokens, 28)
            self.assertEqual(res.token_usage.completion_tokens, 42)
            self.assertEqual(res.token_usage.total_tokens, 70)
            self.assertEqual(len(res.tool_calls), 1)
            self.assertEqual(res.tool_calls[0].name, "lookup_benchmark")
            self.assertEqual(res.tool_calls[0].arguments, {"suite": "ragas"})

    async def test_ollama_http_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(404, json={"error": "model 'not-found' not found"}, request=req)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = OllamaAssistantAdapter(client=client)
            req = ConversationRequest(messages=[Message(role="user", content="Hello")])
            with self.assertRaises(AdapterResponseError) as ctx:
                await adapter.generate(req)
            self.assertEqual(ctx.exception.status_code, 404)
            self.assertIn("not-found", ctx.exception.message)

    async def test_ollama_timeout_error(self):
        def raise_timeout(req):
            raise httpx.TimeoutException("Timed out", request=req)

        transport = httpx.MockTransport(raise_timeout)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = OllamaAssistantAdapter(client=client)
            req = ConversationRequest(messages=[Message(role="user", content="Hello")])
            with self.assertRaises(AdapterConnectionError):
                await adapter.generate(req)


class TestHttpApiAdapter(unittest.IsolatedAsyncioTestCase):
    async def test_http_api_success_and_tool_call_normalization(self):
        mock_response_data = {
            "id": "chatcmpl-test-123",
            "model": "gpt-4o",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Model accuracy is correctness, reliability is stability.",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "check_hallucination",
                                    "arguments": '{"faithfulness_score": 0.96}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 15,
                "completion_tokens": 25,
                "total_tokens": 40,
            },
        }

        captured_request = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured_request["headers"] = dict(request.headers)
            captured_request["body"] = json.loads(request.content.decode("utf-8"))
            return httpx.Response(200, json=mock_response_data, request=request)

        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HttpApiAssistantAdapter(
                base_url="https://api.openai.com/v1",
                api_key="sk-test-secret-key",
                model="gpt-4o",
                client=client,
            )
            req = ConversationRequest(
                system_prompt="You are a grader.",
                messages=[Message(role="user", content="Score response")],
                parameters=GenerationParameters(temperature=0.3, max_tokens=100),
            )
            res = await adapter.generate(req)

            # Verify request headers and payload
            self.assertEqual(captured_request["headers"]["authorization"], "Bearer sk-test-secret-key")
            self.assertEqual(captured_request["body"]["model"], "gpt-4o")
            self.assertEqual(len(captured_request["body"]["messages"]), 2)
            self.assertEqual(captured_request["body"]["messages"][0]["role"], "system")

            # Verify response parsing
            self.assertEqual(res.provider, "http")
            self.assertEqual(res.output, "Model accuracy is correctness, reliability is stability.")
            self.assertEqual(res.token_usage.total_tokens, 40)
            self.assertEqual(len(res.tool_calls), 1)
            self.assertEqual(res.tool_calls[0].name, "check_hallucination")
            self.assertEqual(res.tool_calls[0].arguments, {"faithfulness_score": 0.96})

    async def test_http_api_401_error(self):
        transport = httpx.MockTransport(
            lambda req: httpx.Response(401, json={"error": {"message": "Invalid API key"}}, request=req)
        )
        async with httpx.AsyncClient(transport=transport) as client:
            adapter = HttpApiAssistantAdapter(client=client)
            req = ConversationRequest(messages=[Message(role="user", content="Hi")])
            with self.assertRaises(AdapterResponseError) as ctx:
                await adapter.generate(req)
            self.assertEqual(ctx.exception.status_code, 401)


class TestAdapterRegistry(unittest.TestCase):
    def test_get_mock_adapter(self):
        adapter = get_adapter("mock", model="custom-mock")
        self.assertIsInstance(adapter, MockAssistantAdapter)
        self.assertEqual(adapter.model, "custom-mock")

    def test_get_ollama_adapter(self):
        adapter = get_adapter("ollama", base_url="http://localhost:11434", model="llama3")
        self.assertIsInstance(adapter, OllamaAssistantAdapter)
        self.assertEqual(adapter.model, "llama3")

    def test_get_http_adapter(self):
        adapter = get_adapter("http", base_url="https://api.openai.com/v1", api_key="test-key")
        self.assertIsInstance(adapter, HttpApiAssistantAdapter)

    def test_unknown_provider_raises_error(self):
        with self.assertRaises(AdapterConfigError):
            get_adapter("non_existent_provider")

    def test_custom_adapter_registration(self):
        class CustomAdapter(BaseAssistantAdapter):
            provider_name = "custom"

            async def generate(self, request):
                return AssistantResponse(
                    output="custom",
                    provider="custom",
                    model="custom-v1",
                    latency_ms=1,
                )

        register_adapter("custom", CustomAdapter)
        adapter = get_adapter("custom")
        self.assertIsInstance(adapter, CustomAdapter)


if __name__ == "__main__":
    unittest.main()

