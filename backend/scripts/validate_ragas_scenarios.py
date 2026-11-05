"""Sequential live Ragas checks against controlled fictional BharatHome scenarios.

Run from backend with: python scripts/validate_ragas_scenarios.py
Observed judge results are reported as-is; expected behavior is qualitative and
never feeds into production scoring.
"""
import os
import sys
import time
import uuid

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.config import settings
from app.evaluation.context import EvaluationContext
from app.evaluation.ragas.evaluators import (
    RagasContextPrecisionEvaluator, RagasContextRecallEvaluator, RagasFaithfulnessEvaluator,
)
from app.evaluation.ragas.judge import RagasOllamaJudgeModel
from app.schemas.adapter import AssistantResponse


QUESTION = "What are the capacity and warranty details of the BharatHome ChillPro refrigerator?"
ANSWER = "The BharatHome ChillPro has a 320-litre capacity, a 2-year comprehensive warranty, and a 10-year compressor warranty."

SCENARIOS = [
    ("correct", ["BharatHome ChillPro refrigerator capacity is 320 litres. Its comprehensive warranty is 2 years, and its compressor warranty is 10 years."], "The ChillPro is 320 litres with 2-year comprehensive and 10-year compressor coverage.", "All requested facts are retrieved; recall and precision should generally be high."),
    ("irrelevant", ["BharatHome MixMate mixer has a 750-watt motor and three speed settings.", "BharatHome Spark dishwasher has six wash programs."], ANSWER, "Retrieved chunks are unrelated; context precision should generally be low."),
    ("incomplete", ["BharatHome ChillPro refrigerator capacity is 320 litres."], "The ChillPro is 320 litres.", "Capacity is present, but both warranty facts are absent; recall should be below the complete case."),
    ("contradictory", ["BharatHome ChillPro has 280-litre capacity, a 1-year comprehensive warranty, and a 5-year compressor warranty."], ANSWER, "Retrieved details conflict with the reference; metrics should flag poor support/relevance."),
    ("empty", [], ANSWER, "No context exists; context-dependent metrics should be not_applicable."),
]


def main() -> int:
    judge = RagasOllamaJudgeModel()
    print(f"Ollama: {judge.base_url} | model: {judge.model_name} | sequential")
    if not judge.is_available():
        print(f"LIVE VALIDATION UNAVAILABLE: Ollama/model unavailable at {judge.base_url} ({judge.model_name}).")
        return 2

    evaluators = [
        ("Faithfulness", RagasFaithfulnessEvaluator(model=judge)),
        ("Context Precision", RagasContextPrecisionEvaluator(model=judge)),
        ("Context Recall", RagasContextRecallEvaluator(model=judge)),
    ]
    unexpected = 0
    observed = {}
    for name, contexts, response, expected in SCENARIOS:
        print(f"\n=== {name.upper()} ===\nQuestion: {QUESTION}\nExpected answer: {ANSWER}\nRetrieved context: {contexts}\nAssistant response: {response}\nExpected behavior: {expected}")
        ctx = EvaluationContext(
            test_case_id=uuid.uuid4(), test_case_name=f"BharatHome validation: {name}",
            input_data={"query": QUESTION}, expected_output={"summary": ANSWER},
            retrieval_context=contexts,
            actual_response=AssistantResponse(output=response, provider="validation", model="qwen2.5:1.5b", latency_ms=0),
        )
        scenario_results = {}
        for metric_name, evaluator in evaluators:
            started = time.perf_counter()
            result = evaluator.evaluate(ctx)
            elapsed = time.perf_counter() - started
            reason = result.details.get("reason") or result.details.get("error") or "No judge explanation returned."
            scenario_results[metric_name] = result
            print(f"{metric_name}: score={result.score:.4f}, applicable={result.applicable}, status={result.details.get('status')}, time={elapsed:.2f}s")
            print(f"  Explanation: {reason}")
            for raw in result.details.get("judge_explanations", []):
                print(f"  Judge response: {raw}")
            if result.applicable and not 0 <= result.score <= 1:
                print("  UNEXPECTED: score outside valid range")
                unexpected += 1
        observed[name] = scenario_results
        if name == "empty" and any(result.applicable for result in scenario_results.values()):
            print("  UNEXPECTED: a context-dependent metric was applicable with empty retrieval")
            unexpected += 1
    for scenario, metric, compared, expectation in (
        ("irrelevant", "Context Precision", "correct", "precision should be lower than correct retrieval"),
        ("incomplete", "Context Recall", "correct", "recall should be lower than complete retrieval"),
        ("contradictory", "Faithfulness", "correct", "faithfulness should be lower than supported retrieval"),
        ("contradictory", "Context Precision", "correct", "precision should be lower when retrieved facts contradict the answer"),
        ("contradictory", "Context Recall", "correct", "recall should be lower when answer facts are contradicted by retrieval"),
    ):
        a, b = observed[scenario][metric], observed[compared][metric]
        if a.applicable and b.applicable and a.score >= b.score:
            print(f"UNEXPECTED: {scenario} {metric}={a.score:.4f} was not lower than {compared}={b.score:.4f}; expected {expectation}.")
            unexpected += 1
        elif a.applicable and b.applicable:
            print(f"Observed comparison: {scenario} {metric} {a.score:.4f} < {compared} {b.score:.4f} as expected.")
    print(f"\nValidation completed. Unexpected outcomes: {unexpected}.")
    print("Small-model judgments are fallible; scores are observations, not proof of correctness.")
    return 1 if unexpected else 0


if __name__ == "__main__":
    raise SystemExit(main())
