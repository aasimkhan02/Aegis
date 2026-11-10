"""Evaluation run comparison engine for assessing assistant version improvements and regressions.

Computes comparative performance statistics, metric delta analysis, individual test case
regressions, security vulnerabilities, latency shifts, and overall quality verdicts.
"""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.evaluation.exceptions import (
    ComparisonError,
    EvaluationConfigError,
    IncompatibleProjectError,
)
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.schemas.comparison import (
    ComparisonResponse,
    LatencyComparison,
    MetricComparisonSummary,
    MetricScoreComparison,
    OverallPerformance,
    RegressionAnalysis,
    RunPerformanceSummary,
    TestCaseRegressionDetail,
)

logger = logging.getLogger("aegis.evaluation.comparison")

SECURITY_METRICS = {
    "security_pii",
    "security_canary",
    "security_forbidden_content",
    "security_structured_response",
    "security_policy",
    "technical_safety",
    "promptfoo:jailbreak",
    "promptfoo:prompt-injection",
}

SECURITY_KEYWORDS = [
    "security",
    "jailbreak",
    "injection",
    "adversarial",
    "safety",
    "pii",
    "canary",
    "vulnerability",
    "bypass",
]


def compare_evaluation_runs(
    db: Session,
    baseline_run_id: uuid.UUID,
    candidate_run_id: uuid.UUID,
) -> ComparisonResponse:
    """Compare two completed evaluation runs evaluated against the same golden dataset.

    Args:
        db: Active SQLAlchemy database session.
        baseline_run_id: Target UUID of the baseline evaluation run.
        candidate_run_id: Target UUID of the candidate evaluation run.

    Returns:
        ComparisonResponse with comprehensive comparative metrics and verdict.

    Raises:
        EvaluationConfigError: If either run does not exist.
        ComparisonError: If either run is not completed or uses a different dataset.
        IncompatibleProjectError: If runs belong to different projects.
    """
    # 1. Fetch runs
    baseline_run = db.scalar(
        select(EvaluationRun)
        .options(joinedload(EvaluationRun.assistant_version))
        .where(EvaluationRun.id == baseline_run_id)
    )
    if not baseline_run:
        raise EvaluationConfigError(f"Baseline evaluation run '{baseline_run_id}' not found.")

    candidate_run = db.scalar(
        select(EvaluationRun)
        .options(joinedload(EvaluationRun.assistant_version))
        .where(EvaluationRun.id == candidate_run_id)
    )
    if not candidate_run:
        raise EvaluationConfigError(f"Candidate evaluation run '{candidate_run_id}' not found.")

    # 2. Validate completion status
    if baseline_run.status != "completed":
        raise ComparisonError(
            f"Baseline evaluation run '{baseline_run_id}' is not completed (current status: '{baseline_run.status}')."
        )
    if candidate_run.status != "completed":
        raise ComparisonError(
            f"Candidate evaluation run '{candidate_run_id}' is not completed (current status: '{candidate_run.status}')."
        )

    # 3. Validate matching project
    if baseline_run.project_id != candidate_run.project_id:
        raise IncompatibleProjectError(
            f"Cannot compare runs across different projects: baseline belongs to project '{baseline_run.project_id}', "
            f"candidate belongs to project '{candidate_run.project_id}'."
        )

    # 4. Validate matching dataset
    if baseline_run.dataset_id != candidate_run.dataset_id:
        raise ComparisonError(
            f"Cannot compare runs across different datasets: baseline evaluated dataset '{baseline_run.dataset_id}', "
            f"candidate evaluated dataset '{candidate_run.dataset_id}'."
        )

    # 5. Fetch case results with nested metrics
    baseline_cases = db.scalars(
        select(CaseResult)
        .options(joinedload(CaseResult.metric_results))
        .where(CaseResult.evaluation_run_id == baseline_run_id)
    ).unique().all()

    candidate_cases = db.scalars(
        select(CaseResult)
        .options(joinedload(CaseResult.metric_results))
        .where(CaseResult.evaluation_run_id == candidate_run_id)
    ).unique().all()

    # 6. Latency Analysis
    b_latencies = [cr.latency_ms for cr in baseline_cases if cr.latency_ms is not None]
    c_latencies = [cr.latency_ms for cr in candidate_cases if cr.latency_ms is not None]

    b_avg_latency = round(sum(b_latencies) / len(b_latencies), 2) if b_latencies else None
    c_avg_latency = round(sum(c_latencies) / len(c_latencies), 2) if c_latencies else None

    latency_delta = None
    latency_pct = None
    if b_avg_latency is not None and c_avg_latency is not None:
        latency_delta = round(c_avg_latency - b_avg_latency, 2)
        if b_avg_latency > 0:
            latency_pct = round(((c_avg_latency - b_avg_latency) / b_avg_latency) * 100.0, 2)
        else:
            latency_pct = 0.0

    latency_comp = LatencyComparison(
        baseline_average_ms=b_avg_latency,
        candidate_average_ms=c_avg_latency,
        delta_ms=latency_delta,
        percent_change=latency_pct,
    )

    # 7. Overall Performance
    b_total = baseline_run.total_cases
    b_passed = baseline_run.passed_cases
    b_failed = baseline_run.failed_cases
    b_pass_rate = round((b_passed / b_total * 100.0), 2) if b_total > 0 else 0.0

    c_total = candidate_run.total_cases
    c_passed = candidate_run.passed_cases
    c_failed = candidate_run.failed_cases
    c_pass_rate = round((c_passed / c_total * 100.0), 2) if c_total > 0 else 0.0

    pass_rate_delta = round(c_pass_rate - b_pass_rate, 2)

    b_summary = RunPerformanceSummary(
        run_id=baseline_run.id,
        assistant_version_id=baseline_run.assistant_version_id,
        assistant_name=baseline_run.assistant_version.name if baseline_run.assistant_version else None,
        assistant_version=baseline_run.assistant_version.version if baseline_run.assistant_version else None,
        total_cases=b_total,
        passed_cases=b_passed,
        failed_cases=b_failed,
        pass_rate=b_pass_rate,
        average_latency_ms=b_avg_latency,
    )

    c_summary = RunPerformanceSummary(
        run_id=candidate_run.id,
        assistant_version_id=candidate_run.assistant_version_id,
        assistant_name=candidate_run.assistant_version.name if candidate_run.assistant_version else None,
        assistant_version=candidate_run.assistant_version.version if candidate_run.assistant_version else None,
        total_cases=c_total,
        passed_cases=c_passed,
        failed_cases=c_failed,
        pass_rate=c_pass_rate,
        average_latency_ms=c_avg_latency,
    )

    overall_comp = OverallPerformance(
        total_cases=max(b_total, c_total),
        baseline=b_summary,
        candidate=c_summary,
        pass_rate_delta=pass_rate_delta,
    )

    # 8. Metric Scores Calculation
    def _extract_metric_means(case_list: list[CaseResult]) -> dict[str, float]:
        scores: dict[str, list[float]] = {}
        for cr in case_list:
            for mr in cr.metric_results:
                details = mr.details if isinstance(mr.details, dict) else {}
                # Exclude non-applicable evaluations explicitly
                if details.get("applicable", True) is False:
                    continue
                if mr.score is not None:
                    scores.setdefault(mr.metric_name, []).append(mr.score)

        return {m: round(sum(vals) / len(vals), 4) for m, vals in scores.items() if vals}

    b_metrics = _extract_metric_means(baseline_cases)
    c_metrics = _extract_metric_means(candidate_cases)

    all_metric_names = sorted(set(b_metrics.keys()) | set(c_metrics.keys()))

    metric_comparisons: list[MetricScoreComparison] = []
    improved_metrics: list[str] = []
    degraded_metrics: list[str] = []
    unchanged_metrics: list[str] = []

    for m_name in all_metric_names:
        b_score = b_metrics.get(m_name)
        c_score = c_metrics.get(m_name)

        if b_score is not None and c_score is not None:
            delta = round(c_score - b_score, 4)
            if delta > 0.001:
                st = "improved"
                improved_metrics.append(m_name)
            elif delta < -0.001:
                st = "degraded"
                degraded_metrics.append(m_name)
            else:
                st = "unchanged"
                unchanged_metrics.append(m_name)
        elif b_score is None and c_score is not None:
            delta = None
            st = "only_in_candidate"
        elif b_score is not None and c_score is None:
            delta = None
            st = "only_in_baseline"
        else:
            delta = None
            st = "not_evaluated"

        metric_comparisons.append(
            MetricScoreComparison(
                metric_name=m_name,
                baseline_score=b_score,
                candidate_score=c_score,
                score_delta=delta,
                status=st,
            )
        )

    metric_summary = MetricComparisonSummary(
        metrics=metric_comparisons,
        improved_metrics=improved_metrics,
        degraded_metrics=degraded_metrics,
        unchanged_metrics=unchanged_metrics,
    )

    # 9. Individual Test Case Regressions & Security Checks
    b_map = {cr.test_case_id: cr for cr in baseline_cases}
    c_map = {cr.test_case_id: cr for cr in candidate_cases}

    all_tc_ids = sorted(set(b_map.keys()) | set(c_map.keys()), key=lambda u: str(u))

    regressed_cases: list[TestCaseRegressionDetail] = []
    improved_cases: list[TestCaseRegressionDetail] = []
    both_failed_cases: list[TestCaseRegressionDetail] = []
    security_regressions: list[TestCaseRegressionDetail] = []
    both_passed_count = 0

    for tc_id in all_tc_ids:
        b_cr = b_map.get(tc_id)
        c_cr = c_map.get(tc_id)
        if not b_cr or not c_cr:
            continue

        snapshot = c_cr.test_case_snapshot or b_cr.test_case_snapshot or {}
        name = snapshot.get("name") or str(tc_id)
        tags = snapshot.get("tags") or []
        if isinstance(tags, dict):
            tags = list(tags.keys())
        tag_str = " ".join(str(t).lower() for t in tags)

        failed_metrics = [mr.metric_name for mr in c_cr.metric_results if not mr.passed]
        is_sec = any(kw in tag_str for kw in SECURITY_KEYWORDS) or any(
            m.startswith("security_") or m in SECURITY_METRICS for m in failed_metrics
        )

        detail = TestCaseRegressionDetail(
            test_case_id=tc_id,
            name=name,
            baseline_status=b_cr.status,
            candidate_status=c_cr.status,
            is_security=is_sec,
            error_message=c_cr.error_message if c_cr.status != "passed" else None,
            failed_metrics=failed_metrics,
        )

        if b_cr.status == "passed" and c_cr.status != "passed":
            regressed_cases.append(detail)
            if is_sec:
                security_regressions.append(detail)
        elif b_cr.status != "passed" and c_cr.status == "passed":
            improved_cases.append(detail)
        elif b_cr.status != "passed" and c_cr.status != "passed":
            both_failed_cases.append(detail)
        elif b_cr.status == "passed" and c_cr.status == "passed":
            both_passed_count += 1

    regression_analysis = RegressionAnalysis(
        regressed_cases=regressed_cases,
        improved_cases=improved_cases,
        both_failed_cases=both_failed_cases,
        both_passed_count=both_passed_count,
        security_regressions=security_regressions,
    )

    # 10. Overall Verdict Formulation
    if len(security_regressions) > 0:
        verdict = "regressed"
        verdict_explanation = (
            f"Critical regression: {len(security_regressions)} security-related failure(s) detected in candidate version."
        )
    elif len(regressed_cases) > len(improved_cases) or pass_rate_delta < -0.01:
        verdict = "regressed"
        verdict_explanation = (
            f"Regressed: Pass rate dropped by {abs(pass_rate_delta):.1f}% "
            f"({len(regressed_cases)} regression(s) vs {len(improved_cases)} improvement(s))."
        )
    elif len(improved_cases) > len(regressed_cases) or pass_rate_delta > 0.01:
        verdict = "improved"
        verdict_explanation = (
            f"Improved: Pass rate increased by {pass_rate_delta:.1f}% "
            f"(+{len(improved_cases)} case(s) fixed, {len(regressed_cases)} regression(s))."
        )
    else:
        # Pass rate and test-case counts are equivalent
        if len(degraded_metrics) > len(improved_metrics):
            verdict = "regressed"
            verdict_explanation = (
                f"Regressed: Pass rate is unchanged, but {len(degraded_metrics)} metric(s) degraded "
                f"while {len(improved_metrics)} improved."
            )
        elif len(improved_metrics) > len(degraded_metrics):
            verdict = "improved"
            verdict_explanation = (
                f"Improved: Pass rate is unchanged, but {len(improved_metrics)} metric(s) improved "
                f"while {len(degraded_metrics)} degraded."
            )
        else:
            verdict = "unchanged"
            verdict_explanation = "Unchanged: Performance, pass rates, and metric scores remain consistent with baseline."

    return ComparisonResponse(
        baseline_run_id=baseline_run.id,
        candidate_run_id=candidate_run.id,
        project_id=baseline_run.project_id,
        dataset_id=baseline_run.dataset_id,
        verdict=verdict,
        verdict_explanation=verdict_explanation,
        overall=overall_comp,
        metrics=metric_summary,
        regressions=regression_analysis,
        latency=latency_comp,
        compared_at=datetime.now(timezone.utc),
    )

