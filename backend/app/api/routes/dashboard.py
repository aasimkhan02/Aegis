"""FastAPI endpoints for dashboard metrics and security analytics."""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.evaluation.comparison import SECURITY_KEYWORDS, SECURITY_METRICS
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.dashboard import (
    DashboardStatsResponse,
    SecurityFindingItem,
    SecuritySummaryResponse,
)

router = APIRouter()


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    summary="Get aggregated evaluation and resource statistics for the overview dashboard",
)
def get_dashboard_stats(db: Session = Depends(get_db)) -> DashboardStatsResponse:
    total_proj = db.scalar(select(func.count(Project.id))) or 0
    total_asst = db.scalar(select(func.count(AssistantVersion.id))) or 0
    total_data = db.scalar(select(func.count(Dataset.id))) or 0
    total_runs = db.scalar(select(func.count(EvaluationRun.id))) or 0

    # Aggregate completed runs statistics
    runs_stats = db.execute(
        select(
            func.coalesce(func.sum(EvaluationRun.total_cases), 0),
            func.coalesce(func.sum(EvaluationRun.passed_cases), 0),
            func.coalesce(func.sum(EvaluationRun.failed_cases), 0),
        ).where(EvaluationRun.status == "completed")
    ).first()

    total_cases = int(runs_stats[0]) if runs_stats else 0
    passed_cases = int(runs_stats[1]) if runs_stats else 0
    failed_cases = int(runs_stats[2]) if runs_stats else 0

    overall_pass_rate = round((passed_cases / total_cases * 100.0), 1) if total_cases > 0 else 0.0

    # Average latency across all case results
    avg_latency = db.scalar(
        select(func.avg(CaseResult.latency_ms)).where(CaseResult.latency_ms.is_not(None))
    )
    avg_latency_ms = round(float(avg_latency), 1) if avg_latency is not None else None

    # Count security failures
    sec_metric_failures = db.scalar(
        select(func.count(MetricResult.id)).where(
            (MetricResult.passed.is_(False))
            & (
                (MetricResult.metric_name.in_(SECURITY_METRICS))
                | (MetricResult.metric_name.startswith("security_"))
            )
        )
    ) or 0

    return DashboardStatsResponse(
        total_projects=total_proj,
        total_assistants=total_asst,
        total_datasets=total_data,
        total_evaluation_runs=total_runs,
        total_cases_evaluated=total_cases,
        overall_passed_cases=passed_cases,
        overall_failed_cases=failed_cases,
        overall_pass_rate=overall_pass_rate,
        total_security_failures=sec_metric_failures,
        average_latency_ms=avg_latency_ms,
    )


@router.get(
    "/security",
    response_model=SecuritySummaryResponse,
    summary="Get aggregated security findings and validator breakdown",
)
def get_security_summary(
    limit: int = Query(default=50, ge=1, le=200),
    failed_only: bool = Query(default=False, description="Filter for security failures only"),
    db: Session = Depends(get_db),
) -> SecuritySummaryResponse:
    # Query MetricResults that are security validators
    query = (
        select(MetricResult)
        .options(
            joinedload(MetricResult.case_result).joinedload(CaseResult.evaluation_run).joinedload(EvaluationRun.assistant_version)
        )
        .where(
            (MetricResult.metric_name.in_(SECURITY_METRICS))
            | (MetricResult.metric_name.startswith("security_"))
        )
    )

    if failed_only:
        query = query.where(MetricResult.passed.is_(False))

    metric_results = db.scalars(query.order_by(MetricResult.created_at.desc())).all()

    total_sec_cases = len(metric_results)
    total_sec_failures = sum(1 for mr in metric_results if not mr.passed)
    sec_pass_rate = (
        round(((total_sec_cases - total_sec_failures) / total_sec_cases * 100.0), 1)
        if total_sec_cases > 0
        else 100.0
    )

    # Validator breakdown
    breakdown: dict[str, dict[str, int]] = {}
    findings: list[SecurityFindingItem] = []

    for mr in metric_results:
        v_name = mr.metric_name
        if v_name not in breakdown:
            breakdown[v_name] = {"passed": 0, "failed": 0}

        if mr.passed:
            breakdown[v_name]["passed"] += 1
        else:
            breakdown[v_name]["failed"] += 1

        cr = mr.case_result
        if cr and len(findings) < limit:
            er = cr.evaluation_run
            av = er.assistant_version if er else None
            snapshot = cr.test_case_snapshot or {}
            tc_name = snapshot.get("name") or "Unknown Test Case"

            findings.append(
                SecurityFindingItem(
                    case_result_id=cr.id,
                    run_id=cr.evaluation_run_id,
                    test_case_id=cr.test_case_id,
                    test_case_name=tc_name,
                    assistant_name=av.name if av else None,
                    assistant_version=av.version if av else None,
                    validator_name=v_name,
                    status="passed" if mr.passed else "failed",
                    score=mr.score,
                    error_message=cr.error_message if not mr.passed else None,
                    latency_ms=cr.latency_ms,
                    evaluated_at=mr.created_at,
                )
            )

    return SecuritySummaryResponse(
        total_security_cases=total_sec_cases,
        total_security_failures=total_sec_failures,
        security_pass_rate=sec_pass_rate,
        validator_breakdown=breakdown,
        findings=findings,
    )

