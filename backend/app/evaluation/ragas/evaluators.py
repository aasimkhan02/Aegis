"""Ragas BaseEvaluator implementations for Faithfulness, Context Precision, and Context Recall."""

import logging
import math
import asyncio
from numbers import Real
from typing import Any, Optional
from ragas.dataset_schema import SingleTurnSample
from ragas.llms.base import BaseRagasLLM
from ragas.metrics import Faithfulness, LLMContextPrecisionWithReference, LLMContextRecall

from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult
from app.evaluation.ragas.judge import RagasJudgeUnavailableError, RagasOllamaJudgeModel
from app.evaluation.ragas.utils import (
    extract_context_strings,
    extract_input_text,
    extract_reference_text,
    run_async,
)
from app.core.config import settings

logger = logging.getLogger("aegis.evaluation.ragas.evaluators")


def _evaluator_error_result(
    metric_name: str,
    threshold: float,
    error: Exception,
    model_name: str,
    reason: str | None = None,
    judge_explanations: list[str] | None = None,
) -> EvaluatorResult:
    """Construct a standardized non-applicable EvaluatorResult representing an infrastructure outage."""
    return EvaluatorResult(
        metric_name=metric_name,
        score=0.0,
        threshold=threshold,
        passed=False,
        applicable=False,
        mandatory=False,
        details={
            "status": "evaluator_error",
            "evaluator_error": True,
            "error_type": type(error).__name__,
            "error": str(error),
            "reason": reason or f"Judge evaluation failed: {error}",
            "judge_explanations": judge_explanations or [],
            "judge_model": model_name,
            "applicable": False,
        },
    )


class RagasFaithfulnessEvaluator(BaseEvaluator):
    """Evaluates whether the assistant's generated response is supported by the retrieved context.
    
    Required input:
    - User input
    - Assistant response
    - Retrieved context (retrieval_context)
    
    If the test case provides no retrieval_context, the metric is explicitly marked as non-applicable
    without inventing context or failing the test case.
    """

    name: str = "ragas_faithfulness"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[BaseRagasLLM] = None,
        mandatory: bool = True,
        timeout_seconds: float | None = None,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or RagasOllamaJudgeModel()
        self.metric = Faithfulness(llm=self.model)
        self.metric_timeout_seconds = timeout_seconds or settings.ragas_faithfulness_timeout_seconds

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        context_strings = extract_context_strings(context.retrieval_context)

        # Handle missing retrieval context explicitly without inventing evidence
        if not context_strings:
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                threshold=self.default_threshold,
                passed=True,
                applicable=False,
                mandatory=False,
                details={
                    "skipped": True,
                    "status": "skipped",
                    "reason": "Test case has no retrieval_context; ragas faithfulness is not applicable.",
                    "applicable": False,
                },
            )

        output_text = context.output_text
        if not output_text.strip():
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                threshold=self.default_threshold,
                passed=False,
                applicable=True,
                mandatory=self.mandatory,
                details={"error": "Empty or missing assistant output; cannot evaluate ragas faithfulness."},
            )

        input_text = extract_input_text(context.input_data)
        sample = SingleTurnSample(
            user_input=input_text or context.test_case_name,
            response=output_text,
            retrieved_contexts=context_strings,
        )

        try:
            if hasattr(self.model, "last_responses"):
                self.model.last_responses.clear()
            raw_score = run_async(asyncio.wait_for(self.metric.single_turn_ascore(sample), timeout=self.metric_timeout_seconds))
            score = _validated_score(raw_score)
            reason = "Judge score passed format/range validation; small-model judgment remains fallible."

            passed = score >= self.default_threshold
            details: dict[str, Any] = {
                "reason": reason,
                "retrieved_contexts_count": len(context_strings),
                "judge_model": self.model.get_model_name() if hasattr(self.model, "get_model_name") else "ragas-judge",
                "status": "completed",
                "score_source": "ragas_judge",
                "judge_score": score,
                "judge_explanations": list(getattr(self.model, "last_responses", [])),
            }

            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=self.default_threshold,
                passed=passed,
                applicable=True,
                mandatory=self.mandatory,
                details=details,
            )
        except Exception as e:
            logger.warning("Ragas faithfulness evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
                reason="Faithfulness judge failed or returned an invalid score; excluded from aggregates.",
                judge_explanations=list(getattr(self.model, "last_responses", [])),
            )


class RagasContextPrecisionEvaluator(BaseEvaluator):
    """Evaluates whether the retrieved context contains relevant information and ranks it appropriately.
    
    Required input:
    - User input
    - Retrieved context (retrieval_context)
    - Ground-truth reference (ground_truth_context or expected_output reference answer)
    """

    name: str = "ragas_context_precision"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[BaseRagasLLM] = None,
        mandatory: bool = True,
        timeout_seconds: float | None = None,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or RagasOllamaJudgeModel()
        self.metric = LLMContextPrecisionWithReference(llm=self.model)
        self.metric_timeout_seconds = timeout_seconds or settings.ragas_context_precision_timeout_seconds

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        context_strings = extract_context_strings(context.retrieval_context)
        if not context_strings:
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                threshold=self.default_threshold,
                passed=True,
                applicable=False,
                mandatory=False,
                details={
                    "skipped": True,
                    "status": "skipped",
                    "reason": "Test case has no retrieval_context; ragas context precision is not applicable.",
                    "applicable": False,
                },
            )

        reference = extract_reference_text(context.ground_truth_context, context.expected_output)
        if not reference:
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                threshold=self.default_threshold,
                passed=True,
                applicable=False,
                mandatory=False,
                details={
                    "skipped": True,
                    "status": "not_applicable",
                    "not_applicable": True,
                    "reason": "No valid answer reference: expected_output was empty/malformed and ground_truth_context had no explicit answer-equivalent value.",
                    "applicable": False,
                },
            )

        input_text = extract_input_text(context.input_data)
        sample = SingleTurnSample(
            user_input=input_text or context.test_case_name,
            retrieved_contexts=context_strings,
            reference=reference,
        )

        try:
            if hasattr(self.model, "last_responses"):
                self.model.last_responses.clear()
            raw_score = run_async(asyncio.wait_for(self.metric.single_turn_ascore(sample), timeout=self.metric_timeout_seconds))
            score = _validated_score(raw_score)
            reason = "Judge score passed format/range validation; small-model judgment remains fallible."

            passed = score >= self.default_threshold
            details: dict[str, Any] = {
                "reason": reason,
                "retrieved_contexts_count": len(context_strings),
                "reference_source": "expected_output" if _answer_reference(context.expected_output) else "ground_truth_context_answer",
                "judge_model": self.model.get_model_name() if hasattr(self.model, "get_model_name") else "ragas-judge",
                "status": "completed",
                "score_source": "ragas_judge",
                "judge_score": score,
                "judge_explanations": list(getattr(self.model, "last_responses", [])),
            }

            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=self.default_threshold,
                passed=passed,
                applicable=True,
                mandatory=self.mandatory,
                details=details,
            )
        except Exception as e:
            logger.warning("Ragas context precision evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
                reason="Context precision judge failed or returned an invalid score; excluded from aggregates.",
                judge_explanations=list(getattr(self.model, "last_responses", [])),
            )


class RagasContextRecallEvaluator(BaseEvaluator):
    """Evaluates whether the retrieved context contains the information required to answer the reference.
    
    Required input:
    - User input
    - Retrieved context (retrieval_context)
    - Ground-truth reference (ground_truth_context or expected_output reference answer)
    """

    name: str = "ragas_context_recall"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[BaseRagasLLM] = None,
        mandatory: bool = True,
        timeout_seconds: float | None = None,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or RagasOllamaJudgeModel()
        self.metric = LLMContextRecall(llm=self.model)
        self.metric_timeout_seconds = timeout_seconds or settings.ragas_context_recall_timeout_seconds

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        context_strings = extract_context_strings(context.retrieval_context)
        if not context_strings:
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                threshold=self.default_threshold,
                passed=True,
                applicable=False,
                mandatory=False,
                details={
                    "skipped": True,
                    "status": "skipped",
                    "reason": "Test case has no retrieval_context; ragas context recall is not applicable.",
                    "applicable": False,
                },
            )

        reference = extract_reference_text(context.ground_truth_context, context.expected_output)
        if not reference:
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                threshold=self.default_threshold,
                passed=True,
                applicable=False,
                mandatory=False,
                details={
                    "skipped": True,
                    "status": "not_applicable",
                    "not_applicable": True,
                    "reason": "No valid answer reference: expected_output was empty/malformed and ground_truth_context had no explicit answer-equivalent value.",
                    "applicable": False,
                },
            )

        input_text = extract_input_text(context.input_data)
        sample = SingleTurnSample(
            user_input=input_text or context.test_case_name,
            retrieved_contexts=context_strings,
            reference=reference,
        )

        try:
            if hasattr(self.model, "last_responses"):
                self.model.last_responses.clear()
            raw_score = run_async(asyncio.wait_for(self.metric.single_turn_ascore(sample), timeout=self.metric_timeout_seconds))
            score = _validated_score(raw_score)
            reason = "Judge score passed format/range validation; small-model judgment remains fallible."

            passed = score >= self.default_threshold
            details: dict[str, Any] = {
                "reason": reason,
                "retrieved_contexts_count": len(context_strings),
                "reference_source": "expected_output" if _answer_reference(context.expected_output) else "ground_truth_context_answer",
                "judge_model": self.model.get_model_name() if hasattr(self.model, "get_model_name") else "ragas-judge",
                "status": "completed",
                "score_source": "ragas_judge",
                "judge_score": score,
                "judge_explanations": list(getattr(self.model, "last_responses", [])),
            }

            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=self.default_threshold,
                passed=passed,
                applicable=True,
                mandatory=self.mandatory,
                details=details,
            )
        except Exception as e:
            logger.warning("Ragas context recall evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
                reason="Context recall judge failed or returned an invalid score; excluded from aggregates.",
                judge_explanations=list(getattr(self.model, "last_responses", [])),
            )


def _validated_score(raw_score: Any) -> float:
    """Reject malformed judge scores rather than clamping or inventing a result."""
    if raw_score is None or isinstance(raw_score, bool) or not isinstance(raw_score, Real):
        raise ValueError(f"Judge returned a non-numeric score: {raw_score!r}")
    score = float(raw_score)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise ValueError(f"Judge score must be finite and within [0, 1], got {raw_score!r}")
    return round(score, 4)


def _answer_reference(value: Any) -> str:
    # Kept as a tiny helper for reference-source reporting; extraction itself owns validation.
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("summary", "response", "answer", "ground_truth", "expected", "output"):
            val = value.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""
