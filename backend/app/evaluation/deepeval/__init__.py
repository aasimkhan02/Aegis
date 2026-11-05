"""DeepEval LLM-as-a-judge evaluation integration for Aegis."""

from app.evaluation.deepeval.judge import JudgeUnavailableError, OllamaJudgeModel
from app.evaluation.deepeval.metrics import CustomerTroubleshootingSafetyMetric
from app.evaluation.deepeval.evaluators import (
    DeepEvalAnswerRelevancyEvaluator,
    DeepEvalFaithfulnessEvaluator,
    DeepEvalHallucinationEvaluator,
    DeepEvalTechnicalSafetyEvaluator,
)
from app.evaluation.deepeval.utils import (
    calculate_aggregate_metric_score,
    is_evaluator_error,
    is_metric_applicable,
    is_metric_result_applicable,
    summarize_run_metrics,
)
from app.evaluation.evaluators.base import BaseEvaluator


def get_deepeval_evaluators(
    judge_model: OllamaJudgeModel | None = None,
    threshold: float = 0.5,
    mandatory: bool = True,
) -> list[BaseEvaluator]:
    """Instantiate and return the suite of 4 DeepEval LLM-as-a-judge evaluators.
    
    1. Answer Relevancy
    2. Faithfulness
    3. Hallucination Detection
    4. Technical Safety (CustomerTroubleshootingSafety)
    """
    model = judge_model or OllamaJudgeModel()
    return [
        DeepEvalAnswerRelevancyEvaluator(threshold=threshold, model=model, mandatory=mandatory),
        DeepEvalFaithfulnessEvaluator(threshold=threshold, model=model, mandatory=mandatory),
        DeepEvalHallucinationEvaluator(threshold=threshold, model=model, mandatory=mandatory),
        DeepEvalTechnicalSafetyEvaluator(threshold=threshold, model=model, mandatory=mandatory),
    ]


__all__ = [
    "JudgeUnavailableError",
    "OllamaJudgeModel",
    "CustomerTroubleshootingSafetyMetric",
    "DeepEvalAnswerRelevancyEvaluator",
    "DeepEvalFaithfulnessEvaluator",
    "DeepEvalHallucinationEvaluator",
    "DeepEvalTechnicalSafetyEvaluator",
    "get_deepeval_evaluators",
    "is_evaluator_error",
    "is_metric_applicable",
    "is_metric_result_applicable",
    "calculate_aggregate_metric_score",
    "summarize_run_metrics",
]

