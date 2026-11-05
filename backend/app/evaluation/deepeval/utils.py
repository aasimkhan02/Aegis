"""Utility functions for DeepEval test case preparation and data extraction."""

from typing import Any


def extract_input_text(input_data: Any) -> str:
    """Extract a user query string from various input_data formats.
    
    Supports:
    - Raw string
    - Dict with 'messages': list of role/content dicts
    - Dict with keys: 'query', 'prompt', 'input', 'text', 'customer_query', 'question'
    - Dict with arbitrary key/value pairs
    """
    if not input_data:
        return ""

    if isinstance(input_data, str):
        return input_data.strip()

    if isinstance(input_data, dict):
        # Case 1: Structured conversation messages
        messages = input_data.get("messages")
        if isinstance(messages, list):
            for msg in reversed(messages):
                if isinstance(msg, dict) and msg.get("role") == "user":
                    content = msg.get("content")
                    if content:
                        return str(content).strip()
                elif isinstance(msg, str) and msg.strip():
                    return msg.strip()

        # Case 2: Named query/prompt fields
        for key in ("query", "prompt", "input", "text", "customer_query", "question"):
            val = input_data.get(key)
            if val and str(val).strip():
                return str(val).strip()

        # Case 3: Key-value summary
        parts = [f"{k}: {v}" for k, v in input_data.items() if v]
        if parts:
            return ", ".join(parts)

    return str(input_data).strip()


def extract_context_strings(retrieval_context: Any) -> list[str]:
    """Normalize retrieval context into a list of non-empty text strings.
    
    Supports:
    - list of strings: ["snippet 1", "snippet 2"]
    - list of dicts: [{"text": "..."}, {"content": "..."}, {"snippet": "..."}]
    - single string: "snippet"
    - single dict: {"text": "..."}
    - None or empty structures -> []
    """
    if not retrieval_context:
        return []

    results: list[str] = []

    if isinstance(retrieval_context, str):
        s = retrieval_context.strip()
        if s:
            results.append(s)
        return results

    if isinstance(retrieval_context, dict):
        text = (
            retrieval_context.get("text")
            or retrieval_context.get("content")
            or retrieval_context.get("snippet")
        )
        if text and str(text).strip():
            results.append(str(text).strip())
        elif retrieval_context:
            results.append(str(retrieval_context))
        return results

    if isinstance(retrieval_context, (list, tuple)):
        for item in retrieval_context:
            if isinstance(item, str):
                s = item.strip()
                if s:
                    results.append(s)
            elif isinstance(item, dict):
                text = (
                    item.get("text")
                    or item.get("content")
                    or item.get("snippet")
                )
                if text and str(text).strip():
                    results.append(str(text).strip())
                elif item:
                    results.append(str(item))
            elif item is not None:
                s = str(item).strip()
                if s:
                    results.append(s)

    return results


def is_evaluator_error(details: dict[str, Any] | None) -> bool:
    """Return True if the metric result details indicate an evaluator infrastructure failure."""
    if not isinstance(details, dict):
        return False
    return bool(
        details.get("evaluator_error") is True
        or details.get("status") == "evaluator_error"
        or details.get("error_type") is not None
    )


def is_metric_applicable(details: dict[str, Any] | None) -> bool:
    """Return True if the metric was actively applicable and evaluated (not skipped or errored)."""
    if not isinstance(details, dict):
        return True
    if details.get("applicable") is False or details.get("skipped") is True:
        return False
    if is_evaluator_error(details):
        return False
    return True


def is_metric_result_applicable(mr: Any) -> bool:
    """Determine whether a MetricResult, EvaluatorResult, or dict is valid and applicable.
    
    A metric is considered NON-APPLICABLE if:
    1. It was explicitly skipped or marked non-applicable (applicable=False or skipped=True).
    2. It suffered an evaluator infrastructure failure (evaluator_error=True or status='evaluator_error').
    
    Genuine evaluation failures (score=0.0, applicable=True) return True.
    """
    if mr is None:
        return False

    # Check direct attribute on object (e.g., EvaluatorResult)
    if hasattr(mr, "applicable") and getattr(mr, "applicable") is False:
        return False

    # Check dict keys or nested details
    if isinstance(mr, dict):
        if mr.get("applicable") is False or mr.get("skipped") is True:
            return False
        if mr.get("evaluator_error") is True or mr.get("status") == "evaluator_error":
            return False
        details = mr.get("details")
    else:
        details = getattr(mr, "details", None)

    return is_metric_applicable(details)


def calculate_aggregate_metric_score(metrics: list[Any]) -> float | None:
    """Calculate the arithmetic mean of applicable, non-errored metric scores.
    
    CRITICAL AGGREGATION RULES:
    1. Excludes non-applicable metrics: do not treat score=1.0 on skipped metrics as a real 100%.
    2. Excludes evaluator errors: do not treat score=0.0 on judge crashes as an assistant failure.
    3. Includes genuine failures: score=0.0 where applicable=True MUST be counted.
    4. Empty collections: if no applicable metrics exist, return None (unavailable), NEVER 0.0 or 1.0.
    """
    if not metrics:
        return None

    applicable_scores: list[float] = []
    for m in metrics:
        if is_metric_result_applicable(m):
            if isinstance(m, dict):
                score = m.get("score")
            else:
                score = getattr(m, "score", None)
            if score is not None:
                applicable_scores.append(float(score))

    if not applicable_scores:
        return None

    return round(sum(applicable_scores) / len(applicable_scores), 4)


def summarize_run_metrics(metrics: list[Any]) -> dict[str, Any]:
    """Group metrics by metric_name and compute robust aggregation statistics.
    
    Returns a dictionary containing:
    - by_metric: per-metric breakdown (applicable_count, average_score, pass_rate, skipped_count, error_count)
    - overall_average_score: arithmetic mean across all applicable metrics, or None if none applicable
    - total_metrics: total count of all metric records
    - applicable_metrics: count of applicable metric records
    """
    by_metric: dict[str, dict[str, Any]] = {}
    all_applicable_scores: list[float] = []

    for m in metrics:
        if isinstance(m, dict):
            name = str(m.get("metric_name", "unknown"))
            passed = bool(m.get("passed", False))
            score = float(m.get("score", 0.0))
            details = m.get("details") or {}
        else:
            name = str(getattr(m, "metric_name", "unknown"))
            passed = bool(getattr(m, "passed", False))
            score = float(getattr(m, "score", 0.0))
            details = getattr(m, "details", None) or {}

        if name not in by_metric:
            by_metric[name] = {
                "total_count": 0,
                "applicable_count": 0,
                "skipped_count": 0,
                "error_count": 0,
                "passed_count": 0,
                "scores": [],
            }

        stats = by_metric[name]
        stats["total_count"] += 1

        if is_evaluator_error(details) or (isinstance(m, dict) and m.get("evaluator_error")):
            stats["error_count"] += 1
        elif not is_metric_result_applicable(m):
            stats["skipped_count"] += 1
        else:
            stats["applicable_count"] += 1
            stats["scores"].append(score)
            all_applicable_scores.append(score)
            if passed:
                stats["passed_count"] += 1

    summarized_by_metric: dict[str, dict[str, Any]] = {}
    for name, stats in by_metric.items():
        app_count = stats["applicable_count"]
        avg_score = round(sum(stats["scores"]) / app_count, 4) if app_count > 0 else None
        pass_rate = round(stats["passed_count"] / app_count, 4) if app_count > 0 else None
        summarized_by_metric[name] = {
            "total_count": stats["total_count"],
            "applicable_count": app_count,
            "skipped_count": stats["skipped_count"],
            "error_count": stats["error_count"],
            "average_score": avg_score,
            "pass_rate": pass_rate,
        }

    overall_avg = (
        round(sum(all_applicable_scores) / len(all_applicable_scores), 4)
        if all_applicable_scores
        else None
    )

    return {
        "by_metric": summarized_by_metric,
        "overall_average_score": overall_avg,
        "total_metrics": len(metrics),
        "applicable_metrics": len(all_applicable_scores),
    }


