"""Lightweight deterministic security validators package for Aegis."""

from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.security.canary import CanaryLeakageValidator
from app.evaluation.security.forbidden import ForbiddenContentValidator
from app.evaluation.security.pii import PIIDetectionValidator
from app.evaluation.security.policy import SecurityPolicyValidator
from app.evaluation.security.structured import StructuredResponseValidator

__all__ = [
    "PIIDetectionValidator",
    "CanaryLeakageValidator",
    "ForbiddenContentValidator",
    "StructuredResponseValidator",
    "SecurityPolicyValidator",
    "get_security_evaluators",
]


def get_security_evaluators(validators: list[str] | None = None) -> list[BaseEvaluator]:
    """Retrieve instances of active lightweight security validators.
    
    Args:
        validators: Optional subset of validator names to instantiate.
    """
    all_map = {
        "security_pii": PIIDetectionValidator,
        "security_canary": CanaryLeakageValidator,
        "security_forbidden_content": ForbiddenContentValidator,
        "security_structured_response": StructuredResponseValidator,
        "security_policy": SecurityPolicyValidator,
    }

    if validators:
        selected = []
        for name in validators:
            key = name.lower().strip()
            if key in all_map:
                selected.append(all_map[key]())
        return selected

    return [cls() for cls in all_map.values()]

