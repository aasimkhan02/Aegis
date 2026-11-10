"""Automated Release Quality Gate engine for approving or rejecting assistant versions.

Evaluates candidate assistant versions against configurable release criteria:
- Minimum pass rate
- Maximum permitted regression compared with baseline
- Strict zero security regressions
- Maximum allowed security failures
- Required evaluation metrics availability and applicability
"""

from datetime import datetime, timezone
import logging
from typing import Any
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.evaluation.comparison import SECURITY_KEYWORDS, SECURITY_METRICS, compare_evaluation_runs
from app.models.case_result import CaseResult
from app.models.metric_result import MetricResult
from app.schemas.quality_gate import (
    QualityGateRequest,
    QualityGateResponse,
    QualityGateThresholds,
    RuleEvaluationDetail,
)

logger = logging.getLogger("aegis.evaluation.quality_gate")


def evaluate_release_quality_gate(
    db: Session,
    baseline_run_id: uuid.UUID,
    candidate_run_id: uuid.UUID,
    thresholds: QualityGateThresholds | None = None,
) -> QualityGateResponse:
    """Evaluate candidate assistant version release readiness against configurable criteria.

    Args:
        db: Active SQLAlchemy database session.
        baseline_run_id: UUID of baseline evaluation run.
        candidate_run_id: UUID of candidate evaluation run.
        thresholds: Configurable thresholds (or sensible defaults).

    Returns:
        QualityGateResponse with PASS/FAIL decision and rule-by-rule breakdown.

    Raises:
        EvaluationConfigError: If either run does not exist (404).
        ComparisonError: If either run is incomplete or uses a different dataset (400).
        IncompatibleProjectError: If runs belong to different projects (400).
    """
    if thresholds is None:
        thresholds = QualityGateThresholds()

    # 1. Reuse Step 12 Version Comparison Engine (validates runs, project, dataset, completion)
    comparison = compare_evaluation_runs(
        db=db,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
    )

    # 2. Fetch candidate case results to inspect metric applicability and security checks
    candidate_cases = db.scalars(
        select(CaseResult)
        .options(joinedload(CaseResult.metric_results))
        .where(CaseResult.evaluation_run_id == candidate_run_id)
    ).unique().all()

    rules_evaluated: list[str] = []
    passed_rules: list[str] = []
    failed_rules: list[str] = []
    rule_details: list[RuleEvaluationDetail] = []
    failed_requirements: list[str] = []

    # --------------------------------------------------------------------------
    # Rule A: Minimum Pass Rate
    # --------------------------------------------------------------------------
    rules_evaluated.append("minimum_pass_rate")
    cand_pass_rate = comparison.overall.candidate.pass_rate
    min_required_rate = thresholds.minimum_pass_rate
    rule_a_passed = cand_pass_rate >= min_required_rate

    if rule_a_passed:
        passed_rules.append("minimum_pass_rate")
        msg_a = (
            f"Candidate pass rate of {cand_pass_rate:.1f}% satisfies minimum required "
            f"threshold of {min_required_rate:.1f}%."
        )
    else:
        failed_rules.append("minimum_pass_rate")
        msg_a = (
            f"Candidate pass rate of {cand_pass_rate:.1f}% is below required minimum of "
            f"{min_required_rate:.1f}% (deficit of {min_required_rate - cand_pass_rate:.1f}%)."
        )
        failed_requirements.append(msg_a)

    rule_details.append(
        RuleEvaluationDetail(
            rule_name="minimum_pass_rate",
            passed=rule_a_passed,
            configured_threshold=min_required_rate,
            actual_value=cand_pass_rate,
            message=msg_a,
        )
    )

    # --------------------------------------------------------------------------
    # Rule B: Maximum Regression
    # --------------------------------------------------------------------------
    rules_evaluated.append("maximum_regression")
    base_pass_rate = comparison.overall.baseline.pass_rate
    regression_drop = max(0.0, round(base_pass_rate - cand_pass_rate, 2))
    max_permitted_drop = thresholds.maximum_regression_percentage_points
    rule_b_passed = regression_drop <= max_permitted_drop

    if rule_b_passed:
        passed_rules.append("maximum_regression")
        msg_b = (
            f"Pass rate drop of {regression_drop:.1f}% is within maximum allowed "
            f"regression of {max_permitted_drop:.1f}%."
        )
    else:
        failed_rules.append("maximum_regression")
        msg_b = (
            f"Candidate pass rate dropped by {regression_drop:.1f}% compared to baseline, "
            f"exceeding maximum permitted regression of {max_permitted_drop:.1f}%."
        )
        failed_requirements.append(msg_b)

    rule_details.append(
        RuleEvaluationDetail(
            rule_name="maximum_regression",
            passed=rule_b_passed,
            configured_threshold=max_permitted_drop,
            actual_value=regression_drop,
            message=msg_b,
        )
    )

    # --------------------------------------------------------------------------
    # Rule C1: Strict Zero Security Regressions
    # --------------------------------------------------------------------------
    rules_evaluated.append("security_regression")
    sec_reg_count = len(comparison.regressions.security_regressions)
    rule_c1_passed = sec_reg_count == 0

    if rule_c1_passed:
        passed_rules.append("security_regression")
        msg_c1 = "Zero security regressions detected."
    else:
        failed_rules.append("security_regression")
        msg_c1 = (
            f"Critical security regression: {sec_reg_count} security test case(s) that "
            "passed in baseline failed in candidate."
        )
        failed_requirements.append(msg_c1)

    rule_details.append(
        RuleEvaluationDetail(
            rule_name="security_regression",
            passed=rule_c1_passed,
            configured_threshold=0,
            actual_value=sec_reg_count,
            message=msg_c1,
        )
    )

    # --------------------------------------------------------------------------
    # Rule C2: Maximum Permitted Security Failures in Candidate
    # --------------------------------------------------------------------------
    rules_evaluated.append("maximum_security_failures")
    cand_sec_failures = 0
    for cr in candidate_cases:
        if cr.status != "passed":
            snapshot = cr.test_case_snapshot or {}
            tags = snapshot.get("tags") or []
            if isinstance(tags, dict):
                tags = list(tags.keys())
            tag_str = " ".join(str(t).lower() for t in tags)
            failed_mrs = [mr for mr in cr.metric_results if not mr.passed]

            is_sec = any(kw in tag_str for kw in SECURITY_KEYWORDS) or any(
                mr.metric_name.startswith("security_") or mr.metric_name in SECURITY_METRICS
                for mr in failed_mrs
            )
            if is_sec:
                cand_sec_failures += 1

    max_sec_failures = thresholds.maximum_security_failures
    rule_c2_passed = cand_sec_failures <= max_sec_failures

    if rule_c2_passed:
        passed_rules.append("maximum_security_failures")
        msg_c2 = (
            f"Candidate had {cand_sec_failures} security failure(s) (maximum allowed: {max_sec_failures})."
        )
    else:
        failed_rules.append("maximum_security_failures")
        msg_c2 = (
            f"Candidate had {cand_sec_failures} security failure(s), exceeding maximum "
            f"permitted threshold of {max_sec_failures}."
        )
        failed_requirements.append(msg_c2)

    rule_details.append(
        RuleEvaluationDetail(
            rule_name="maximum_security_failures",
            passed=rule_c2_passed,
            configured_threshold=max_sec_failures,
            actual_value=cand_sec_failures,
            message=msg_c2,
        )
    )

    # --------------------------------------------------------------------------
    # Rule D: Required Metrics Availability & Applicability
    # --------------------------------------------------------------------------
    if thresholds.required_metrics:
        rules_evaluated.append("required_metrics")

        # Map candidate metrics by name
        cand_metrics_map: dict[str, list[MetricResult]] = {}
        for cr in candidate_cases:
            for mr in cr.metric_results:
                cand_metrics_map.setdefault(mr.metric_name, []).append(mr)

        req_failures: list[str] = []

        for req_metric in thresholds.required_metrics:
            mrs = cand_metrics_map.get(req_metric)
            if not mrs:
                req_failures.append(
                    f"Required metric '{req_metric}' was not evaluated in candidate run."
                )
                continue

            # Check for applicable instances (non-applicable must not silently count as passing!)
            applicable_mrs = [
                mr for mr in mrs
                if (mr.details.get("applicable", True) if isinstance(mr.details, dict) else True)
                and mr.score is not None
            ]
            if not applicable_mrs:
                req_failures.append(
                    f"Required metric '{req_metric}' has no applicable evaluations in candidate run (all instances marked non-applicable or missing scores)."
                )
                continue

            # Check if any applicable test case failed the required metric
            failed_metric_cases = sum(1 for mr in applicable_mrs if not mr.passed)
            if failed_metric_cases > 0:
                req_failures.append(
                    f"Required metric '{req_metric}' failed in {failed_metric_cases} test case(s)."
                )

        rule_d_passed = len(req_failures) == 0

        if rule_d_passed:
            passed_rules.append("required_metrics")
            msg_d = (
                f"All required metrics ({', '.join(thresholds.required_metrics)}) were evaluated, "
                "applicable, and satisfied in candidate run."
            )
        else:
            failed_rules.append("required_metrics")
            msg_d = f"Required metric requirement(s) failed: {'; '.join(req_failures)}"
            failed_requirements.extend(req_failures)

        rule_details.append(
            RuleEvaluationDetail(
                rule_name="required_metrics",
                passed=rule_d_passed,
                configured_threshold=thresholds.required_metrics,
                actual_value=[
                    m for m in thresholds.required_metrics if m in cand_metrics_map
                ],
                message=msg_d,
            )
        )

    # --------------------------------------------------------------------------
    # Overall Release Decision
    # --------------------------------------------------------------------------
    all_passed = len(failed_rules) == 0
    decision = "PASS" if all_passed else "FAIL"

    # Security regression strictly overrides all other metrics
    if not rule_c1_passed:
        explanation = (
            f"RELEASE REJECTED (CRITICAL SECURITY FAILURE): Candidate introduced {sec_reg_count} "
            "security-related regression(s). Security regressions strictly override all other metrics."
        )
    elif not all_passed:
        explanation = (
            f"RELEASE REJECTED: Candidate failed {len(failed_rules)} quality gate requirement(s): "
            f"{'; '.join(failed_requirements)}."
        )
    else:
        explanation = (
            f"RELEASE APPROVED: Candidate satisfied all release criteria: pass rate of "
            f"{cand_pass_rate:.1f}% (min required: {min_required_rate:.1f}%), regression drop of "
            f"{regression_drop:.1f}% (max permitted: {max_permitted_drop:.1f}%), and zero security regressions."
        )

    return QualityGateResponse(
        decision=decision,
        passed=all_passed,
        baseline_run_id=baseline_run_id,
        candidate_run_id=candidate_run_id,
        project_id=comparison.project_id,
        dataset_id=comparison.dataset_id,
        thresholds=thresholds,
        rules_evaluated=rules_evaluated,
        passed_rules=passed_rules,
        failed_rules=failed_rules,
        rule_details=rule_details,
        failed_requirements=failed_requirements,
        explanation=explanation,
        evaluated_at=datetime.now(timezone.utc),
    )

