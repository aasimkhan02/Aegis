"""Evaluators package for Aegis evaluation engine."""

from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult
from app.evaluation.evaluators.expected_output import ExpectedOutputEvaluator
from app.evaluation.evaluators.registry import (
    get_default_evaluators,
    get_evaluator,
    register_evaluator,
    resolve_evaluators,
)
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.evaluators.tool_usage import ToolUsageEvaluator
from app.evaluation.ragas import (
    RagasContextPrecisionEvaluator,
    RagasContextRecallEvaluator,
    RagasFaithfulnessEvaluator,
    get_ragas_evaluators,
)

__all__ = [
    "BaseEvaluator",
    "EvaluatorResult",
    "ResponsePresenceEvaluator",
    "ExpectedOutputEvaluator",
    "ToolUsageEvaluator",
    "get_default_evaluators",
    "get_evaluator",
    "register_evaluator",
    "resolve_evaluators",
    "RagasFaithfulnessEvaluator",
    "RagasContextPrecisionEvaluator",
    "RagasContextRecallEvaluator",
    "get_ragas_evaluators",
]

