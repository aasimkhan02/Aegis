"""Base evaluator interface and evaluation result definitions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.evaluation.context import EvaluationContext


@dataclass
class EvaluatorResult:
    """Standardized output produced by any evaluator."""

    metric_name: str
    score: float
    passed: bool
    threshold: float | None = None
    applicable: bool = True
    mandatory: bool = True
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Enforce PostgreSQL check constraints: score between 0.0 and 1.0
        if not (0.0 <= self.score <= 1.0):
            self.score = max(0.0, min(1.0, float(self.score)))

        # Enforce threshold range constraint if provided
        if self.threshold is not None and not (0.0 <= self.threshold <= 1.0):
            self.threshold = max(0.0, min(1.0, float(self.threshold)))


class BaseEvaluator(ABC):
    """Abstract base class that all Aegis evaluators must implement."""

    name: str = "base_evaluator"
    mandatory: bool = True
    default_threshold: float = 1.0

    @abstractmethod
    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        """Evaluate an assistant's response in the given evaluation context.

        Args:
            context: Standardized EvaluationContext containing input, expectations,
                     and actual response.

        Returns:
            EvaluatorResult: Normalized metric name, score, threshold, pass status,
                             and structured details.
        """
        pass

