"""Dry-run test for evaluating all 40 cases on both assistants."""

import json
from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from app.demo.orchestrator import DemoAssistantOrchestrator
from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators.expected_output import ExpectedOutputEvaluator
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.evaluators.tool_usage import ToolUsageEvaluator
from app.schemas.adapter import ConversationRequest, Message, GenerationParameters

data_path = backend_root / "data" / "bharathome_golden_dataset.json"
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cases = data["test_cases"]

orch_v1 = DemoAssistantOrchestrator("v1", simulated_latency_ms=0)
orch_v2 = DemoAssistantOrchestrator("v2", simulated_latency_ms=0)

resp_eval = ResponsePresenceEvaluator()
exp_eval = ExpectedOutputEvaluator()
tool_eval = ToolUsageEvaluator()

print(f"--- TESTING GOOD ASSISTANT (V1) ---")
v1_passed = 0
v1_failed = 0
for idx, tc in enumerate(cases, 1):
    q = tc["input_data"]["messages"][0]["content"]
    req = ConversationRequest(messages=[Message(role="user", content=q)])
    if tc.get("retrieval_context"):
        req.parameters.extra["retrieval_context"] = tc["retrieval_context"]

    # Generate synchronously
    resp = orch_v1._generate_v1_good(req, q, 0.0)

    ctx = EvaluationContext(
        test_case_id=tc.get("id"),
        test_case_name=tc["name"],
        input_data=tc["input_data"],
        expected_output=tc.get("expected_output"),
        expected_behavior=tc.get("expected_behavior"),
        retrieval_context=tc.get("retrieval_context"),
        tags=tc.get("tags", []),
        metadata=tc.get("metadata", {}),
        actual_response=resp,
        latency_ms=resp.latency_ms,
    )

    r_resp = resp_eval.evaluate(ctx)
    r_exp = exp_eval.evaluate(ctx)
    r_tool = tool_eval.evaluate(ctx)

    case_passed = r_resp.passed and (not r_exp.applicable or r_exp.passed) and (not r_tool.applicable or r_tool.passed)
    if case_passed:
        v1_passed += 1
    else:
        v1_failed += 1
        print(f"FAIL #{idx:02d}: {tc['name']}")
        print(f"     Exp details: {r_exp.details}")
        if r_tool.applicable and not r_tool.passed:
            print(f"     Tool details: {r_tool.details}")

print(f"\nV1 Results: {v1_passed} PASSED, {v1_failed} FAILED out of {len(cases)} cases.")

print(f"\n--- TESTING BROKEN ASSISTANT (V2) ---")
v2_passed = 0
v2_failed = 0
for idx, tc in enumerate(cases, 1):
    q = tc["input_data"]["messages"][0]["content"]
    req = ConversationRequest(messages=[Message(role="user", content=q)])
    if tc.get("retrieval_context"):
        req.parameters.extra["retrieval_context"] = tc["retrieval_context"]

    # Generate synchronously
    resp = orch_v2._generate_v2_broken(req, q, 0.0)

    ctx = EvaluationContext(
        test_case_id=tc.get("id"),
        test_case_name=tc["name"],
        input_data=tc["input_data"],
        expected_output=tc.get("expected_output"),
        expected_behavior=tc.get("expected_behavior"),
        retrieval_context=tc.get("retrieval_context"),
        tags=tc.get("tags", []),
        metadata=tc.get("metadata", {}),
        actual_response=resp,
        latency_ms=resp.latency_ms,
    )

    r_resp = resp_eval.evaluate(ctx)
    r_exp = exp_eval.evaluate(ctx)
    r_tool = tool_eval.evaluate(ctx)

    case_passed = r_resp.passed and (not r_exp.applicable or r_exp.passed) and (not r_tool.applicable or r_tool.passed)
    if case_passed:
        v2_passed += 1
        print(f"UNEXPECTED PASS #{idx:02d}: {tc['name']}")
    else:
        v2_failed += 1

print(f"\nV2 Results: {v2_passed} PASSED, {v2_failed} FAILED out of {len(cases)} cases.")

