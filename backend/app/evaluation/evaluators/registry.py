"""Evaluator registry and discovery helper."""

from typing import Any, Type

from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.evaluators.expected_output import ExpectedOutputEvaluator
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.evaluators.tool_usage import ToolUsageEvaluator
from app.evaluation.deepeval.evaluators import (
    DeepEvalAnswerRelevancyEvaluator,
    DeepEvalFaithfulnessEvaluator,
    DeepEvalHallucinationEvaluator,
    DeepEvalTechnicalSafetyEvaluator,
)
from app.evaluation.deepeval import get_deepeval_evaluators
from app.evaluation.ragas import get_ragas_evaluators
from app.evaluation.ragas.evaluators import (
    RagasContextPrecisionEvaluator,
    RagasContextRecallEvaluator,
    RagasFaithfulnessEvaluator,
)
from app.evaluation.security import (
    CanaryLeakageValidator,
    ForbiddenContentValidator,
    PIIDetectionValidator,
    SecurityPolicyValidator,
    StructuredResponseValidator,
    get_security_evaluators,
)

_EVALUATOR_REGISTRY: dict[str, Type[BaseEvaluator]] = {
    "response_presence": ResponsePresenceEvaluator,
    "expected_output": ExpectedOutputEvaluator,
    "tool_usage": ToolUsageEvaluator,
    "deepeval_answer_relevancy": DeepEvalAnswerRelevancyEvaluator,
    "deepeval_faithfulness": DeepEvalFaithfulnessEvaluator,
    "deepeval_hallucination": DeepEvalHallucinationEvaluator,
    "deepeval_technical_safety": DeepEvalTechnicalSafetyEvaluator,
    "ragas_faithfulness": RagasFaithfulnessEvaluator,
    "ragas_context_precision": RagasContextPrecisionEvaluator,
    "ragas_context_recall": RagasContextRecallEvaluator,
    "security_pii": PIIDetectionValidator,
    "security_canary": CanaryLeakageValidator,
    "security_forbidden_content": ForbiddenContentValidator,
    "security_structured_response": StructuredResponseValidator,
    "security_policy": SecurityPolicyValidator,
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


def resolve_evaluators(config: dict[str, Any] | None = None) -> list[BaseEvaluator]:
    """Resolve active evaluators for an evaluation run based on run configuration.

    - Default: returns standard deterministic evaluators.
    - If config contains 'enable_deepeval': True, appends the 4 DeepEval evaluators.
    - If config contains explicit 'evaluators': list of registered evaluator names, resolves those.
    """
    cfg = dict(config or {})

    # Check for explicit evaluator selection
    evaluator_names = cfg.get("evaluators")
    if isinstance(evaluator_names, list) and evaluator_names:
        return [get_evaluator(name) for name in evaluator_names]

    evaluators = get_default_evaluators()
    if cfg.get("enable_deepeval") is True or cfg.get("enable_llm_judge") is True:
        evaluators.extend(get_deepeval_evaluators())
    if cfg.get("enable_ragas") is True:
        ragas_names = cfg.get("ragas_metrics")
        evaluators.extend(get_ragas_evaluators(metric_names=ragas_names))
    if cfg.get("enable_security") is True or cfg.get("enable_security_validators") is True:
        sec_names = cfg.get("security_validators")
        evaluators.extend(get_security_evaluators(validators=sec_names))

    return evaluators

