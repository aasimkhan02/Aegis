"""Pydantic schemas for Automated Release Quality Gate."""

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, ConfigDict, Field


class QualityGateThresholds(BaseModel):
    """Configurable release criteria thresholds."""

    model_config = ConfigDict(extra="allow")

    minimum_pass_rate: float = Field(
        default=90.0,
        ge=0.0,
        le=100.0,
        description="Minimum candidate pass rate percentage required for release (default: 90.0%)",
    )
    maximum_regression_percentage_points: float = Field(
        default=5.0,
        ge=0.0,
        le=100.0,
        description="Maximum permitted drop in pass rate compared to baseline (default: 5.0 percentage points)",
    )
    maximum_security_failures: int = Field(
        default=0,
        ge=0,
        description="Maximum permitted security check failures in candidate (default: 0)",
    )
    required_metrics: list[str] = Field(
        default_factory=list,
        description="List of evaluation metric names that must be present, applicable, and evaluated on candidate",
    )


class QualityGateRequest(BaseModel):
    """Request payload to evaluate candidate assistant version release readiness."""

    baseline_run_id: uuid.UUID = Field(..., description="UUID of baseline evaluation run")
    candidate_run_id: uuid.UUID = Field(..., description="UUID of candidate evaluation run")
    thresholds: QualityGateThresholds = Field(default_factory=QualityGateThresholds)


class RuleEvaluationDetail(BaseModel):
    """Detailed outcome of an individual quality gate rule."""

    rule_name: str
    passed: bool
    configured_threshold: Any
    actual_value: Any
    message: str


class QualityGateResponse(BaseModel):
    """Automated release quality gate decision report."""

    decision: str = Field(..., description="'PASS' or 'FAIL'")
    passed: bool
    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    thresholds: QualityGateThresholds
    rules_evaluated: list[str] = Field(default_factory=list)
    passed_rules: list[str] = Field(default_factory=list)
    failed_rules: list[str] = Field(default_factory=list)
    rule_details: list[RuleEvaluationDetail] = Field(default_factory=list)
    failed_requirements: list[str] = Field(default_factory=list)
    explanation: str
    evaluated_at: datetime

