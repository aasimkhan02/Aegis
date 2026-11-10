"""Pydantic schemas for Evaluation API endpoints."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class EvaluationConfigPayload(BaseModel):
    """Execution options controlling concurrency and error thresholds."""

    model_config = ConfigDict(extra="allow")

    max_concurrency: int = Field(default=1, ge=1, le=3, description="Concurrency limit (default: 1)")
    fail_fast: bool = Field(default=False, description="Abort run upon first test failure")
    enable_deepeval: bool = Field(default=False, description="Enable DeepEval LLM-as-a-judge metrics")
    enable_ragas: bool = Field(default=False, description="Enable Ragas RAG evaluation metrics")
    ragas_metrics: list[str] | None = Field(default=None, description="Optional explicit subset of Ragas metric names")
    enable_security: bool = Field(default=False, description="Enable lightweight deterministic security validators")
    security_validators: list[str] | None = Field(default=None, description="Optional explicit subset of security validator names")
    evaluators: list[str] | None = Field(default=None, description="Optional explicit list of evaluator names")
    extra: dict[str, Any] = Field(default_factory=dict)


class EvaluationCreateRequest(BaseModel):
    """Payload to initiate an evaluation run."""

    assistant_version_id: uuid.UUID = Field(..., description="Target assistant version UUID")
    dataset_id: uuid.UUID = Field(..., description="Target golden dataset UUID")
    config: EvaluationConfigPayload = Field(default_factory=EvaluationConfigPayload)


class MetricResultResponse(BaseModel):
    """Metric outcome representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    case_result_id: uuid.UUID
    metric_name: str
    score: float
    threshold: float | None = None
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class CaseResultResponse(BaseModel):
    """Detailed case result representation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    evaluation_run_id: uuid.UUID
    test_case_id: uuid.UUID
    status: str
    error_message: str | None = None
    latency_ms: int | None = None
    test_case_snapshot: dict[str, Any] = Field(default_factory=dict)
    actual_output: dict[str, Any] | None = None
    created_at: datetime
    metric_results: list[MetricResultResponse] = Field(default_factory=list)


class EvaluationRunResponse(BaseModel):
    """Evaluation run metadata and progress."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    project_id: uuid.UUID
    assistant_version_id: uuid.UUID
    dataset_id: uuid.UUID
    status: str
    total_cases: int
    passed_cases: int
    failed_cases: int
    config: dict[str, Any] = Field(default_factory=dict)
    project_name: str | None = None
    assistant_name: str | None = None
    assistant_version_tag: str | None = None
    dataset_name: str | None = None
    pass_rate: float | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime


class EvaluationRunListResponse(BaseModel):
    """Bounded paginated list of evaluation runs."""

    items: list[EvaluationRunResponse]
    total: int


class CaseResultListResponse(BaseModel):
    """Paginated list of case results."""

    items: list[CaseResultResponse]
    total: int

