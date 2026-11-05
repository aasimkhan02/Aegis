"""Evaluation execution engine for Aegis."""

from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators import (
    BaseEvaluator,
    EvaluatorResult,
    ExpectedOutputEvaluator,
    ResponsePresenceEvaluator,
    ToolUsageEvaluator,
    get_default_evaluators,
    get_evaluator,
)
from app.evaluation.exceptions import (
    AssistantResolutionError,
    EvaluationConfigError,
    EvaluationError,
    EvaluationExecutionError,
    IncompatibleProjectError,
)
from app.evaluation.executor import (
    TestCaseExecutionResult,
    build_conversation_request,
    create_test_case_snapshot,
    execute_test_case,
    resolve_assistant_adapter,
)
from app.evaluation.orchestrator import (
    create_evaluation_run,
    execute_evaluation_run,
    validate_evaluation_entities,
)

__all__ = [
    "EvaluationContext",
    "BaseEvaluator",
    "EvaluatorResult",
    "ResponsePresenceEvaluator",
    "ExpectedOutputEvaluator",
    "ToolUsageEvaluator",
    "get_default_evaluators",
    "get_evaluator",
    "EvaluationError",
    "EvaluationConfigError",
    "IncompatibleProjectError",
    "AssistantResolutionError",
    "EvaluationExecutionError",
    "TestCaseExecutionResult",
    "build_conversation_request",
    "create_test_case_snapshot",
    "execute_test_case",
    "resolve_assistant_adapter",
    "create_evaluation_run",
    "execute_evaluation_run",
    "validate_evaluation_entities",
]

