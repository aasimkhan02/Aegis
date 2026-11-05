"""Evaluator registry and discovery helper."""

from typing import Type

from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.evaluators.expected_output import ExpectedOutputEvaluator
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.evaluators.tool_usage import ToolUsageEvaluator

_EVALUATOR_REGISTRY: dict[str, Type[BaseEvaluator]] = {
    "response_presence": ResponsePresenceEvaluator,
    "expected_output": ExpectedOutputEvaluator,
    "tool_usage": ToolUsageEvaluator,
}


def register_evaluator(name: str, evaluator_cls: Type[BaseEvaluator]) -> None:
    """Register a custom evaluator class."""
    _EVALUATOR_REGISTRY[name.lower().strip()] = evaluator_cls


def get_evaluator(name: str) -> BaseEvaluator:
    """Instantiate an evaluator by registered name."""
    key = name.lower().strip()
    cls = _EVALUATOR_REGISTRY.get(key)
    if not cls:
        raise KeyError(f"Unknown evaluator '{name}'. Registered: {list(_EVALUATOR_REGISTRY.keys())}")
    return cls()


def get_default_evaluators() -> list[BaseEvaluator]:
    """Retrieve instances of all standard deterministic evaluators."""
    return [
        ResponsePresenceEvaluator(),
        ExpectedOutputEvaluator(),
        ToolUsageEvaluator(),
    ]

