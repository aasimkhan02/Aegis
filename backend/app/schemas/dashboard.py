"""Pydantic schemas for aggregated dashboard metrics and security analytics."""

from datetime import datetime
from typing import Any
import uuid
from pydantic import BaseModel, Field


class DashboardStatsResponse(BaseModel):
    total_projects: int = 0
    total_assistants: int = 0
    total_datasets: int = 0
    total_evaluation_runs: int = 0
    total_cases_evaluated: int = 0
    overall_passed_cases: int = 0
    overall_failed_cases: int = 0
    overall_pass_rate: float = 0.0
    total_security_failures: int = 0
    average_latency_ms: float | None = None


class SecurityFindingItem(BaseModel):
    case_result_id: uuid.UUID
    run_id: uuid.UUID
    test_case_id: uuid.UUID
    test_case_name: str
    assistant_name: str | None = None
    assistant_version: str | None = None
    validator_name: str
    status: str
    score: float
    error_message: str | None = None
    latency_ms: int | None = None
    evaluated_at: datetime


class SecuritySummaryResponse(BaseModel):
    total_security_cases: int = 0
    total_security_failures: int = 0
    security_pass_rate: float = 0.0
    validator_breakdown: dict[str, dict[str, int]] = Field(default_factory=dict)
    findings: list[SecurityFindingItem] = Field(default_factory=list)

