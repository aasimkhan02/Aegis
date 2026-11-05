"""Response presence evaluator ensuring non-empty assistant responses."""

from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult


class ResponsePresenceEvaluator(BaseEvaluator):
    """Evaluates whether the assistant returned a non-empty, usable response."""

    name: str = "response_presence"
    mandatory: bool = True
    default_threshold: float = 1.0

    def __init__(self, default_threshold: float = 1.0) -> None:
        self.default_threshold = default_threshold

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        if not context.actual_response:
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                threshold=self.default_threshold,
                passed=False,
                applicable=True,
                mandatory=self.mandatory,
                details={
                    "error": context.error_message or "No response received from assistant.",
                    "is_empty": True,
                    "output_length": 0,
                },
            )

        output = context.actual_response.output.strip()
        length = len(output)
        is_empty = length == 0

        score = 0.0 if is_empty else 1.0
        passed = score >= self.default_threshold

        return EvaluatorResult(
            metric_name=self.name,
            score=score,
            threshold=self.default_threshold,
            passed=passed,
            applicable=True,
            mandatory=self.mandatory,
            details={
                "output_length": length,
                "is_empty": is_empty,
                "provider": context.actual_response.provider,
                "model": context.actual_response.model,
                "latency_ms": context.latency_ms,
            },
        )
