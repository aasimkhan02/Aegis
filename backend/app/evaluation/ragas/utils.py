"""Utility functions for Ragas evaluation data extraction and execution."""

import asyncio
from typing import Any
import nest_asyncio

from app.evaluation.deepeval.utils import (
    extract_context_strings,
    extract_input_text,
    is_evaluator_error,
    is_metric_applicable,
)


def run_async(coro: Any) -> Any:
    """Run an async coroutine synchronously, safely handling running event loops in any environment."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        nest_asyncio.apply(loop)
        return loop.run_until_complete(coro)
    else:
        return asyncio.run(coro)


def _answer_text(value: Any) -> str:
    """Extract only clearly answer-shaped data, never arbitrary evidence chunks."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("summary", "response", "answer", "ground_truth", "expected", "output"):
            candidate = value.get(key)
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()
            if isinstance(candidate, dict):
                nested = _answer_text(candidate)
                if nested:
                    return nested
        return ""
    if isinstance(value, list):
        # Lists of answer claims are valid; lists of strings/chunks are ambiguous evidence.
        claims = [item.strip() for item in value if isinstance(item, str) and item.strip()]
        return "\n".join(claims) if claims and len(claims) == len(value) else ""
    return ""


def extract_reference_text(ground_truth_context: Any, expected_output: Any) -> str:
    """Prefer the expected answer; use ground_truth_context only when explicitly answer-shaped."""
    reference = _answer_text(expected_output)
    if reference:
        return reference
    # A free-text ground_truth_context is commonly a source document. Only an explicit
    # answer field makes its semantic role unambiguous.
    if isinstance(ground_truth_context, dict):
        return _answer_text(ground_truth_context)
    if isinstance(ground_truth_context, list):
        answer_items = [item for item in ground_truth_context if isinstance(item, dict)]
        if answer_items and len(answer_items) == len(ground_truth_context):
            return "\n".join(filter(None, (_answer_text(item) for item in answer_items)))
    return ""


def is_ragas_evaluator_error(details: dict[str, Any] | None) -> bool:
    """Return True if details indicate a Ragas evaluator infrastructure failure."""
    return is_evaluator_error(details)


def is_ragas_metric_applicable(details: dict[str, Any] | None) -> bool:
    """Return True if the Ragas metric was actively applicable and evaluated."""
    return is_metric_applicable(details)

