"""Controlled live validation of HallucinationMetric using local Ollama (qwen2.5:1.5b).

Tests:
Scenario A: Factually supported response (should pass, high score)
Scenario B: Direct factual contradiction (should fail, substantially lower score)
"""

import os
import sys
import time
import uuid

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.evaluation.context import EvaluationContext
from app.evaluation.deepeval.evaluators import DeepEvalHallucinationEvaluator
from app.evaluation.deepeval.judge import OllamaJudgeModel
from app.schemas.adapter import AssistantResponse


def run_scenarios() -> None:
    print("=" * 80)
    print("CONTROLLED LIVE HALLUCINATION EVALUATOR VALIDATION")
    print("=" * 80)
    print(f"Ollama Judge: {settings.ollama_base_url} ({settings.ollama_default_model})")

    judge = OllamaJudgeModel()
    if not judge.is_available():
        print(f"[ERROR] Ollama judge is not available at {judge.base_url}")
        sys.exit(1)

    print("[SUCCESS] Ollama daemon reachable.\n")

    evaluator = DeepEvalHallucinationEvaluator(threshold=0.5, model=judge)

    ground_truth = [
        "The BharatHome AeroCool ceiling fan has a 2-year motor warranty. Physical damage is not covered by the warranty."
    ]

    # Scenario A: Factually supported
    print("--- SCENARIO A: Factually Supported Response ---")
    ctx_a = EvaluationContext(
        test_case_id=uuid.uuid4(),
        test_case_name="AeroCool Fan Warranty - Supported",
        input_data={"query": "What is the warranty on the BharatHome AeroCool ceiling fan?"},
        ground_truth_context=ground_truth,
        retrieval_context=None,  # Must NOT use retrieval_context
        actual_response=AssistantResponse(
            output="The BharatHome AeroCool ceiling fan includes a 2-year motor warranty. Physical damage is excluded from warranty coverage.",
            provider="ollama",
            model="bharathome-v1",
            latency_ms=100,
        ),
    )

    t0 = time.perf_counter()
    res_a = evaluator.evaluate(ctx_a)
    dur_a = time.perf_counter() - t0

    print(f"Scenario A Score:     {res_a.score:.4f}")
    print(f"Scenario A Threshold: {res_a.threshold}")
    print(f"Scenario A Passed:    {res_a.passed}")
    print(f"Scenario A Latency:   {dur_a:.2f}s")
    print(f"Scenario A Reason:    {res_a.details.get('reason')}\n")

    # Scenario B: Direct factual contradiction
    print("--- SCENARIO B: Direct Factual Contradiction ---")
    ctx_b = EvaluationContext(
        test_case_id=uuid.uuid4(),
        test_case_name="AeroCool Fan Warranty - Contradiction",
        input_data={"query": "What is the warranty on the BharatHome AeroCool ceiling fan?"},
        ground_truth_context=ground_truth,
        retrieval_context=None,  # Must NOT use retrieval_context
        actual_response=AssistantResponse(
            output="The BharatHome AeroCool ceiling fan has a 5-year motor warranty. Physical damage is fully covered by the warranty.",
            provider="ollama",
            model="bharathome-v1",
            latency_ms=100,
        ),
    )

    t0 = time.perf_counter()
    res_b = evaluator.evaluate(ctx_b)
    dur_b = time.perf_counter() - t0

    print(f"Scenario B Score:     {res_b.score:.4f}")
    print(f"Scenario B Threshold: {res_b.threshold}")
    print(f"Scenario B Passed:    {res_b.passed}")
    print(f"Scenario B Latency:   {dur_b:.2f}s")
    print(f"Scenario B Reason:    {res_b.details.get('reason')}\n")

    print("=" * 80)
    print("COMPARISON & VERIFICATION SUMMARY:")
    print(f"  Scenario A (Supported):     Score={res_a.score:.4f}, Passed={res_a.passed}")
    print(f"  Scenario B (Contradiction): Score={res_b.score:.4f}, Passed={res_b.passed}")
    diff = res_a.score - res_b.score
    print(f"  Score Separation:           {diff:+.4f}")
    if res_a.score > res_b.score and res_a.passed and not res_b.passed:
        print("  [SUCCESS] Metric successfully differentiated between supported and contradicted output!")
    else:
        print(f"  [RESULT] Inspection required. Detailed explanation in report.")
    print("=" * 80)


if __name__ == "__main__":
    run_scenarios()

