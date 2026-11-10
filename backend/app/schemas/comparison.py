"""Pydantic schemas for Evaluation Version Comparison endpoints."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class ComparisonRequest(BaseModel):
    """Payload to request comparison between two completed evaluation runs."""

    baseline_run_id: uuid.UUID = Field(..., description="UUID of the baseline evaluation run")
    candidate_run_id: uuid.UUID = Field(..., description="UUID of the candidate evaluation run")


class RunPerformanceSummary(BaseModel):
    """Overall summary statistics for a single evaluation run."""

    model_config = ConfigDict(from_attributes=True)

    run_id: uuid.UUID
    assistant_version_id: uuid.UUID
    assistant_name: str | None = None
    assistant_version: str | None = None
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float = Field(..., description="Pass rate percentage (0.0 to 100.0)")
    average_latency_ms: float | None = None


class OverallPerformance(BaseModel):
    """Comparative performance between baseline and candidate runs."""

    total_cases: int
    baseline: RunPerformanceSummary
    candidate: RunPerformanceSummary
    pass_rate_delta: float = Field(
        ...,
        description="Candidate pass rate minus baseline pass rate in percentage points",
    )


class MetricScoreComparison(BaseModel):
    """Score comparison for an individual metric across runs."""

    metric_name: str
    baseline_score: float | None = None
    candidate_score: float | None = None
    score_delta: float | None = None
    status: str = Field(
        ...,
        description="'improved', 'degraded', 'unchanged', 'only_in_candidate', 'only_in_baseline', or 'not_evaluated'",
    )


class MetricComparisonSummary(BaseModel):
    """Summary of metric comparisons across all evaluated metrics."""

    metrics: list[MetricScoreComparison] = Field(default_factory=list)
    improved_metrics: list[str] = Field(default_factory=list)
    degraded_metrics: list[str] = Field(default_factory=list)
    unchanged_metrics: list[str] = Field(default_factory=list)


class TestCaseRegressionDetail(BaseModel):
    """Detailed record of a test case transition between baseline and candidate."""

    test_case_id: uuid.UUID
    name: str
    baseline_status: str
    candidate_status: str
    is_security: bool = False
    error_message: str | None = None
    failed_metrics: list[str] = Field(default_factory=list)


class RegressionAnalysis(BaseModel):
    """Categorized test-case outcomes comparing baseline and candidate runs."""

    regressed_cases: list[TestCaseRegressionDetail] = Field(default_factory=list)
    improved_cases: list[TestCaseRegressionDetail] = Field(default_factory=list)
    both_failed_cases: list[TestCaseRegressionDetail] = Field(default_factory=list)
    both_passed_count: int = 0
    security_regressions: list[TestCaseRegressionDetail] = Field(default_factory=list)


class LatencyComparison(BaseModel):
    """Latency comparison between baseline and candidate runs."""

    baseline_average_ms: float | None = None
    candidate_average_ms: float | None = None
    delta_ms: float | None = None
    percent_change: float | None = None


class ComparisonResponse(BaseModel):
    """Complete version comparison report between two evaluation runs."""

    baseline_run_id: uuid.UUID
    candidate_run_id: uuid.UUID
    project_id: uuid.UUID
    dataset_id: uuid.UUID
    verdict: str = Field(..., description="'improved', 'regressed', or 'unchanged'")
    verdict_explanation: str
    overall: OverallPerformance
    metrics: MetricComparisonSummary
    regressions: RegressionAnalysis
    latency: LatencyComparison
    compared_at: datetime

