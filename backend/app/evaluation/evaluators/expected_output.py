"""Expected output evaluator with support for keyword match, exact match, contains, and json."""

import json
from typing import Any

from app.evaluation.context import EvaluationContext
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult


class ExpectedOutputEvaluator(BaseEvaluator):
    """Compares the assistant response against machine-readable expected assertions."""

    name: str = "expected_output"
    mandatory: bool = True
    default_threshold: float = 0.5

    def __init__(self, default_threshold: float = 0.5) -> None:
        self.default_threshold = default_threshold

    def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
        if not context.actual_response or not context.actual_response.output:
            return EvaluatorResult(
                metric_name=self.name,
                score=0.0,
                threshold=self.default_threshold,
                passed=False,
                applicable=True,
                mandatory=self.mandatory,
                details={"error": "Cannot evaluate expected output on empty response."},
            )

        output = context.actual_response.output
        output_lower = output.lower()

        eval_cfg = context.metadata.get("evaluation", {})
        expected = context.expected_output or {}

        # Determine evaluation mode: explicit match_type, or detect from expected_output keys
        match_type = eval_cfg.get("match_type") or expected.get("match_type")
        threshold = float(eval_cfg.get("minimum_match_ratio") or expected.get("threshold") or self.default_threshold)

        # ----------------------------------------------------------------------
        # Mode 1: Keywords / must_include matching
        # ----------------------------------------------------------------------
        must_include = eval_cfg.get("expected_keywords") or expected.get("must_include")
        if match_type == "keywords" or (must_include and isinstance(must_include, list)):
            keywords = must_include if isinstance(must_include, list) else []
            if not keywords:
                return EvaluatorResult(
                    metric_name=self.name,
                    score=1.0,
                    threshold=threshold,
                    passed=True,
                    applicable=False,
                    mandatory=self.mandatory,
                    details={"applicable": False, "reason": "Empty keywords list in expected_output."},
                )

            matched: list[str] = []
            missed: list[str] = []
            for kw in keywords:
                if str(kw).lower() in output_lower:
                    matched.append(str(kw))
                else:
                    missed.append(str(kw))

            match_ratio = round(len(matched) / len(keywords), 4)
            passed = match_ratio >= threshold

            # Check optional prohibited keywords (must_not_include)
            prohibited = expected.get("must_not_include", [])
            found_prohibited = [p for p in prohibited if str(p).lower() in output_lower]
            if found_prohibited:
                passed = False

            return EvaluatorResult(
                metric_name=self.name,
                score=match_ratio,
                threshold=threshold,
                passed=passed,
                applicable=True,
                mandatory=self.mandatory,
                details={
                    "mode": "keywords",
                    "total_keywords": len(keywords),
                    "matched_count": len(matched),
                    "matched": matched,
                    "missed": missed,
                    "match_ratio": match_ratio,
                    "threshold": threshold,
                    "found_prohibited": found_prohibited,
                },
            )

        # ----------------------------------------------------------------------
        # Mode 2: Exact string matching
        # ----------------------------------------------------------------------
        if match_type == "exact" or "exact" in expected:
            expected_text = str(expected.get("exact") or expected.get("text", "")).strip()
            actual_text = output.strip()
            is_match = actual_text == expected_text
            score = 1.0 if is_match else 0.0
            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=1.0,
                passed=is_match,
                applicable=True,
                mandatory=self.mandatory,
                details={
                    "mode": "exact",
                    "expected": expected_text,
                    "actual_length": len(actual_text),
                    "is_match": is_match,
                },
            )

        # ----------------------------------------------------------------------
        # Mode 3: Substring contains
        # ----------------------------------------------------------------------
        if match_type == "contains" or "contains" in expected:
            substring = str(expected.get("contains") or expected.get("substring", "")).strip()
            is_present = substring.lower() in output_lower
            score = 1.0 if is_present else 0.0
            return EvaluatorResult(
                metric_name=self.name,
                score=score,
                threshold=1.0,
                passed=is_present,
                applicable=True,
                mandatory=self.mandatory,
                details={
                    "mode": "contains",
                    "expected_substring": substring,
                    "is_present": is_present,
                },
            )

        # ----------------------------------------------------------------------
        # Mode 4: JSON equality
        # ----------------------------------------------------------------------
        if match_type == "json_equal" or "json" in expected:
            expected_json = expected.get("json", {})
            try:
                actual_json = json.loads(output)
                is_equal = actual_json == expected_json
                score = 1.0 if is_equal else 0.0
                return EvaluatorResult(
                    metric_name=self.name,
                    score=score,
                    threshold=1.0,
                    passed=is_equal,
                    applicable=True,
                    mandatory=self.mandatory,
                    details={
                        "mode": "json_equal",
                        "is_equal": is_equal,
                        "expected_json": expected_json,
                    },
                )
            except Exception as e:
                return EvaluatorResult(
                    metric_name=self.name,
                    score=0.0,
                    threshold=1.0,
                    passed=False,
                    applicable=True,
                    mandatory=self.mandatory,
                    details={"mode": "json_equal", "error": f"Failed to parse output as JSON: {e}"},
                )

        # ----------------------------------------------------------------------
        # Non-applicable: No machine-readable assertion found
        # ----------------------------------------------------------------------
        return EvaluatorResult(
            metric_name=self.name,
            score=1.0,
            threshold=threshold,
            passed=True,
            applicable=False,
            mandatory=False,
            details={
                "applicable": False,
                "reason": (
                    "No machine-readable expected output assertion found. "
                    "Evaluation skipped without inventing a synthetic score."
                ),
            },
        )
