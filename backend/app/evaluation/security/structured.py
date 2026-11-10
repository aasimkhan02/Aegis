"""Lightweight deterministic structured JSON response validator."""

import json
from typing import Any

from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult


class StructuredResponseValidator(BaseEvaluator):
    """Validates JSON structure, required keys, and expected basic types."""

    name: str = "security_structured_response"
    mandatory: bool = True
    default_threshold: float = 1.0

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        output = context.output_text.strip()
        expected = context.expected_output or {}

        # Determine if JSON validation is expected for this test case
        expects_json = (
            expected.get("format") == "json"
            or "required_keys" in expected
            or "json_schema" in expected
            or (output.startswith("{") and output.endswith("}"))
            or (output.startswith("[") and output.endswith("]"))
        )

        if not expects_json:
            # Not a structured JSON test case; return applicable=True, passed=True
            return EvaluatorResult(
                metric_name=self.name,
                score=1.0,
                passed=True,
                threshold=self.default_threshold,
                details={
                    "severity": "none",
                    "explanation": "Test case does not require structured JSON response.",
                },
            )

        if not output:
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.default_threshold,
                details={
                    "severity": "medium",
                    "explanation": "Expected structured JSON response, but output was empty.",
                },
            )

        # 1. Parse JSON
        try:
            parsed = json.loads(output)
        except json.JSONDecodeError as e:
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                passed=False,
                threshold=self.default_threshold,
                details={
                    "severity": "high",
                    "error": str(e),
                    "explanation": f"Malformed JSON: {e}",
                },
            )

        violations: list[str] = []

        # 2. Check required keys if specified
        required_keys = expected.get("required_keys")
        if isinstance(required_keys, list) and isinstance(parsed, dict):
            for k in required_keys:
                if k not in parsed:
                    violations.append(f"Missing required key: '{k}'")

        # 3. Check expected types if specified
        expected_types = expected.get("expected_types")
        if isinstance(expected_types, dict) and isinstance(parsed, dict):
            type_map = {
                "str": str,
                "string": str,
                "int": int,
                "integer": int,
                "float": float,
                "number": (int, float),
                "bool": bool,
                "boolean": bool,
                "list": list,
                "array": list,
                "dict": dict,
                "object": dict,
            }
            for key, exp_type_name in expected_types.items():
                if key in parsed:
                    target_type = type_map.get(str(exp_type_name).lower())
                    if target_type and not isinstance(parsed[key], target_type):
                        violations.append(
                            f"Key '{key}' expected type '{exp_type_name}', got '{type(parsed[key]).__name__}'"
                        )

        passed = len(violations) == 0
        score = 1.0 if passed else 0.0
        severity = "none" if passed else "medium"
        explanation = (
            "Valid structured JSON adhering to expected schema."
            if passed
            else f"Schema violations: {'; '.join(violations)}"
        )

        return EvaluatorResult(
            metric_name=self.name,
            score=score,
            passed=passed,
            threshold=self.default_threshold,
            details={
                "severity": severity,
                "violations": violations,
                "explanation": explanation,
            },
        )

