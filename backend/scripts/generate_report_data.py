"""Query PostgreSQL to extract exact report metrics for the latest runs."""

import json
from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select, func
from app.db.session import SessionLocal
from app.models.case_result import CaseResult
from app.models.metric_result import MetricResult
from app.models.evaluation_run import EvaluationRun

RUN_A_ID = "47558c01-26e8-4da2-ad99-a20f4e1025ef"
RUN_B_ID = "89537c12-b212-41ac-8b99-433babfbf07e"

db = SessionLocal()
try:
    run_a = db.scalar(select(EvaluationRun).where(EvaluationRun.id == RUN_A_ID))
    run_b = db.scalar(select(EvaluationRun).where(EvaluationRun.id == RUN_B_ID))

    cases_a = db.scalars(select(CaseResult).where(CaseResult.evaluation_run_id == RUN_A_ID).order_by(CaseResult.created_at)).all()
    cases_b = db.scalars(select(CaseResult).where(CaseResult.evaluation_run_id == RUN_B_ID).order_by(CaseResult.created_at)).all()

    print(f"Run A: ID={run_a.id}, Status={run_a.status}, Passed={run_a.passed_cases}/{run_a.total_cases}")
    print(f"Run B: ID={run_b.id}, Status={run_b.status}, Passed={run_b.passed_cases}/{run_b.total_cases}")

    # Category breakdown
    cat_summary = {}
    for ca, cb in zip(cases_a, cases_b):
        cat = ca.test_case_snapshot.get("metadata", {}).get("category", "Uncategorized")
        if cat not in cat_summary:
            cat_summary[cat] = {"total": 0, "v1_pass": 0, "v2_pass": 0}
        cat_summary[cat]["total"] += 1
        if ca.status == "passed":
            cat_summary[cat]["v1_pass"] += 1
        if cb.status == "passed":
            cat_summary[cat]["v2_pass"] += 1

    print("\n--- Category Breakdown ---")
    for cat, data in cat_summary.items():
        v1_pct = (data["v1_pass"] / data["total"]) * 100
        v2_pct = (data["v2_pass"] / data["total"]) * 100
        print(f"{cat:<40} | Total: {data['total']} | v1: {data['v1_pass']}/{data['total']} ({v1_pct:.0f}%) | v2: {data['v2_pass']}/{data['total']} ({v2_pct:.0f}%)")

finally:
    db.close()

