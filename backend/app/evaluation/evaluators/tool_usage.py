"""Tool usage evaluator to verify expected tool selection and invocation."""

from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult


class ToolUsageEvaluator(BaseEvaluator):
    """Evaluates whether the assistant selected and invoked expected tools."""

    name: str = "tool_usage"
    mandatory: bool = True
    default_threshold: float = 1.0

    def __init__(self, default_threshold: float = 1.0) -> None:
        self.default_threshold = default_threshold

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        eval_cfg = context.metadata.get("evaluation", {})
        expected_tools = eval_cfg.get("expected_tools")

        if not expected_tools and isinstance(context.expected_output, dict):
            expected_tools = context.expected_output.get("expected_tools")

        # If test case does not specify tool expectations, mark as non-applicable
        if not expected_tools or not isinstance(expected_tools, list):
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                threshold=self.default_threshold,
                passed=True,
                applicable=False,
                mandatory=False,
                details={
                    "applicable": False,
                    "reason": "No tool expectations defined for this test case.",
                },
            )

        if not context.actual_response:
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                threshold=self.default_threshold,
                passed=False,
                applicable=True,
                mandatory=self.mandatory,
                details={
                    "error": "No response received to evaluate tool calls.",
                    "expected_tools": expected_tools,
                    "actual_tools": [],
                },
            )

        actual_tools = [tc.name for tc in context.actual_response.tool_calls]
        matched = [t for t in expected_tools if t in actual_tools]
        missing = [t for t in expected_tools if t not in actual_tools]
        unexpected = [t for t in actual_tools if t not in expected_tools]

        score = round(len(matched) / len(expected_tools), 4) if expected_tools else 1.0
        passed = score >= self.default_threshold

        return EvaluatorResult(
            metric_name=self.name,
            score=score,
            threshold=self.default_threshold,
            passed=passed,
            applicable=True,
            mandatory=self.mandatory,
            details={
                "expected_tools": expected_tools,
                "actual_tools": actual_tools,
                "matched": matched,
                "missing": missing,
                "unexpected": unexpected,
            },
        )
