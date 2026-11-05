"""Custom exceptions for the evaluation pipeline."""


class EvaluationError(Exception):
    """Base exception for all evaluation errors."""

    def __init__(self, message: str, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class EvaluationConfigError(EvaluationError):
    """Raised when an evaluation configuration or entity association is invalid."""
    pass


class IncompatibleProjectError(EvaluationConfigError):
    """Raised when assistant version and dataset belong to different projects."""
    pass


class AssistantResolutionError(EvaluationError):
    """Raised when an assistant adapter cannot be resolved or instantiated."""
    pass


class EvaluatorError(EvaluationError):
    """Raised when an evaluator fails during metric computation."""
    pass


class EvaluationExecutionError(EvaluationError):
    """Raised when a catastrophic runtime failure interrupts an evaluation run."""
    pass

