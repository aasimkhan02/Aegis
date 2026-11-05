"""Ragas RAG Evaluation integration for Aegis."""

import os

# Disable Ragas anonymous telemetry by default to protect user privacy and avoid network stalls
os.environ.setdefault("RAGAS_DO_NOT_TRACK", "true")

from ragas.llms.base import BaseRagasLLM

from app.evaluation.evaluators.base import BaseEvaluator
from app.evaluation.ragas.embeddings import (
    MockRagasEmbeddings,
    RagasEmbeddingUnavailableError,
    RagasOllamaEmbeddings,
)
from app.evaluation.ragas.evaluators import (
    RagasContextPrecisionEvaluator,
    RagasContextRecallEvaluator,
    RagasFaithfulnessEvaluator,
)
from app.evaluation.ragas.judge import (
    MockRagasJudgeModel,
    RagasJudgeUnavailableError,
    RagasOllamaJudgeModel,
)
from app.evaluation.ragas.utils import (
    extract_reference_text,
    is_ragas_evaluator_error,
    is_ragas_metric_applicable,
)


def get_ragas_evaluators(
    judge_model: BaseRagasLLM | None = None,
    threshold: float = 0.5,
    mandatory: bool = True,
    metric_names: list[str] | None = None,
) -> list[BaseEvaluator]:
    """Instantiate and return the suite of Ragas RAG evaluators.
    
    1. ragas_faithfulness
    2. ragas_context_precision
    3. ragas_context_recall
    
    Optionally filters by explicit metric_names.
    """
    model = judge_model or RagasOllamaJudgeModel()
    all_evaluators: list[BaseEvaluator] = [
        RagasFaithfulnessEvaluator(threshold=threshold, model=model, mandatory=mandatory),
        RagasContextPrecisionEvaluator(threshold=threshold, model=model, mandatory=mandatory),
        RagasContextRecallEvaluator(threshold=threshold, model=model, mandatory=mandatory),
    ]

    if not metric_names:
        return all_evaluators

    selected_names = {name.lower().strip() for name in metric_names}
    return [ev for ev in all_evaluators if ev.name.lower() in selected_names]


__all__ = [
    "RagasJudgeUnavailableError",
    "RagasOllamaJudgeModel",
    "MockRagasJudgeModel",
    "RagasEmbeddingUnavailableError",
    "RagasOllamaEmbeddings",
    "MockRagasEmbeddings",
    "RagasFaithfulnessEvaluator",
    "RagasContextPrecisionEvaluator",
    "RagasContextRecallEvaluator",
    "get_ragas_evaluators",
    "extract_reference_text",
    "is_ragas_evaluator_error",
    "is_ragas_metric_applicable",
]

