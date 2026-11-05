"""DeepEval LLM-as-a-judge evaluators integrated into Aegis BaseEvaluator architecture."""

import logging
from typing import Any, Optional

from deepeval.metrics import (
    AnswerRelevancyMetric,
    FaithfulnessMetric,
    HallucinationMetric,
)
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase

from app.evaluation.context import EvaluationContext
from app.evaluation.deepeval.judge import JudgeUnavailableError, OllamaJudgeModel
from app.evaluation.deepeval.metrics import CustomerTroubleshootingSafetyMetric
from app.evaluation.deepeval.utils import extract_context_strings, extract_input_text
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult

logger = logging.getLogger("aegis.deepeval.evaluators")


def _evaluator_error_result(metric_name: str, threshold: float, error: Exception, model_name: str) -> EvaluatorResult:
    """Standardized representation for evaluator infrastructure failures.
    
    Guarantees:
    - applicable=False and mandatory=False so the assistant's pass rate is NOT penalized.
    - Explicit 'status': 'evaluator_error' and 'evaluator_error': True in details.
    - Sanitized diagnostic message preserving error type without leaking secrets.
    """
    clean_error = str(error)
    # Remove sensitive connection credentials or tokens if present
    for secret in ("password", "api_key", "token", "secret"):
        if secret in clean_error.lower():
            clean_error = f"{type(error).__name__}: Infrastructure communication failure."
            break

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
            "error": clean_error,
            "judge_model": model_name,
            "applicable": False,
        },
    )


class DeepEvalAnswerRelevancyEvaluator(BaseEvaluator):
    """Evaluates whether the assistant's output directly addresses the user query."""

    name: str = "deepeval_answer_relevancy"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[DeepEvalBaseLLM] = None,
        mandatory: bool = True,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or OllamaJudgeModel()

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        output_text = context.output_text

        if not output_text.strip():
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                threshold=self.default_threshold,
                passed=False,
                applicable=True,
                mandatory=self.mandatory,
                details={"error": "Empty or missing assistant output; cannot evaluate answer relevancy."},
            )

        input_text = extract_input_text(context.input_data)
        test_case = LLMTestCase(
            input=input_text or context.test_case_name,
            actual_output=output_text,
        )

        try:
            metric = AnswerRelevancyMetric(
                threshold=self.default_threshold,
                model=self.model,
                async_mode=False,
            )
            score = float(metric.measure(test_case))
            passed = bool(metric.is_successful())
            details: dict[str, Any] = {
                "reason": metric.reason or "",
                "judge_model": self.model.get_model_name(),
                "status": "completed",
            }
            if hasattr(metric, "statements") and metric.statements:
                details["statements"] = [str(s) for s in metric.statements]

            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=self.default_threshold,
                passed=passed,
                applicable=True,
                mandatory=self.mandatory,
                details=details,
            )
        except (JudgeUnavailableError, Exception) as e:
            logger.warning("Answer relevancy evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
            )


class DeepEvalFaithfulnessEvaluator(BaseEvaluator):
    """Evaluates whether the response is fully supported by the supplied retrieval context.
    
    If the test case provides no retrieval context, the metric is explicitly marked as non-applicable
    without inventing evidence or failing the test case.
    """

    name: str = "deepeval_faithfulness"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[DeepEvalBaseLLM] = None,
        mandatory: bool = True,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or OllamaJudgeModel()

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
                    "reason": "Test case has no retrieval_context; faithfulness evaluation is not applicable.",
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
                details={"error": "Empty or missing assistant output; cannot evaluate faithfulness."},
            )

        input_text = extract_input_text(context.input_data)
        test_case = LLMTestCase(
            input=input_text or context.test_case_name,
            actual_output=output_text,
            retrieval_context=context_strings,
        )

        try:
            metric = FaithfulnessMetric(
                threshold=self.default_threshold,
                model=self.model,
                async_mode=False,
            )
            score = float(metric.measure(test_case))
            passed = bool(metric.is_successful())
            details: dict[str, Any] = {
                "reason": metric.reason or "",
                "context_chunks_evaluated": len(context_strings),
                "judge_model": self.model.get_model_name(),
                "status": "completed",
            }
            if hasattr(metric, "truths") and metric.truths:
                details["truths"] = [str(t) for t in metric.truths]
            if hasattr(metric, "claims") and metric.claims:
                details["claims"] = [str(c) for c in metric.claims]

            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=self.default_threshold,
                passed=passed,
                applicable=True,
                mandatory=self.mandatory,
                details=details,
            )
        except (JudgeUnavailableError, Exception) as e:
            logger.warning("Faithfulness evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
            )


class DeepEvalHallucinationEvaluator(BaseEvaluator):
    """Evaluates whether the response contains claims unsupported by trusted ground-truth context.
    
    CRITICAL DISTINCTION:
    - Faithfulness uses 'retrieval_context' (documents retrieved by the application).
    - Hallucination uses 'ground_truth_context' (curated, trusted reference information).
    - 'expected_output' is never substituted for ground_truth_context.
    
    If the test case provides no ground_truth_context, the metric is explicitly marked as non-applicable
    without running the judge on invented references.
    """

    name: str = "deepeval_hallucination"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[DeepEvalBaseLLM] = None,
        mandatory: bool = True,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or OllamaJudgeModel()

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        # Strictly use ground_truth_context (do NOT substitute retrieval_context or expected_output)
        context_strings = extract_context_strings(context.ground_truth_context)

        # Handle missing ground truth context explicitly without fabricating ground truth
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
                    "reason": "Test case has no ground_truth_context; hallucination evaluation is not applicable.",
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
                details={"error": "Empty or missing assistant output; cannot evaluate hallucination."},
            )

        input_text = extract_input_text(context.input_data)
        # DeepEval HallucinationMetric strictly expects 'context' (list of reference ground truth strings)
        test_case = LLMTestCase(
            input=input_text or context.test_case_name,
            actual_output=output_text,
            context=context_strings,
        )

        try:
            metric = HallucinationMetric(
                threshold=self.default_threshold,
                model=self.model,
                async_mode=False,
            )
            score = float(metric.measure(test_case))
            # DeepEval 4.3.3: 1.0 represents complete alignment, 0.0 represents contradiction/hallucination.
            # Passes when score >= threshold.
            passed = bool(metric.is_successful())
            details: dict[str, Any] = {
                "reason": metric.reason or "",
                "ground_truth_contexts_count": len(context_strings),
                "judge_model": self.model.get_model_name(),
                "status": "completed",
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
        except (JudgeUnavailableError, Exception) as e:
            logger.warning("Hallucination evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
            )


class DeepEvalTechnicalSafetyEvaluator(BaseEvaluator):
    """Evaluates whether troubleshooting advice adheres to appliance safety standards."""

    name: str = "deepeval_technical_safety"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(
        self,
        threshold: float = 0.5,
        model: Optional[DeepEvalBaseLLM] = None,
        mandatory: bool = True,
    ):
        self.default_threshold = threshold
        self.mandatory = mandatory
        self.model = model or OllamaJudgeModel()

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        output_text = context.output_text
        if not output_text.strip():
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                threshold=self.default_threshold,
                passed=False,
                applicable=True,
                mandatory=self.mandatory,
                details={"error": "Empty or missing assistant output; cannot evaluate technical safety."},
            )

        input_text = extract_input_text(context.input_data)
        test_case = LLMTestCase(
            input=input_text or context.test_case_name,
            actual_output=output_text,
        )

        try:
            metric = CustomerTroubleshootingSafetyMetric(
                threshold=self.default_threshold,
                model=self.model,
                async_mode=False,
            )
            score = float(metric.measure(test_case))
            passed = bool(metric.is_successful())
            details: dict[str, Any] = {
                "reason": metric.reason or "",
                "criteria": metric.criteria,
                "evaluation_steps": metric.evaluation_steps,
                "judge_model": self.model.get_model_name(),
                "status": "completed",
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
        except (JudgeUnavailableError, Exception) as e:
            logger.warning("Technical safety evaluation failed due to evaluator error: %s", e)
            return _evaluator_error_result(
                metric_name=self.name,
                threshold=self.default_threshold,
                error=e,
                model_name=self.model.get_model_name() if hasattr(self.model, "get_model_name") else "unknown",
            )
