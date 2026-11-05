"""Inspect metric results and find the exact discrepancy between Run A and Run B."""

from pathlib import Path
import sys

backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.case_result import CaseResult
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult


def inspect_discrepancy() -> None:
    db: Session = SessionLocal()
    try:
        runs = db.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.project_id == "6f37b662-2f09-42c8-89fd-13861044f747")
            .order_by(EvaluationRun.created_at.desc())
            .limit(2)
        ).all()

        if len(runs) < 2:
            print("Fewer than 2 runs found.")
            return

        run_b = runs[0]  # latest is Run B (v2)
        run_a = runs[1]  # previous is Run A (v1)

        print(f"Run A (v1 Good): ID={run_a.id}, Total={run_a.total_cases}, Passed={run_a.passed_cases}, Failed={run_a.failed_cases}")
        print(f"Run B (v2 Broken): ID={run_b.id}, Total={run_b.total_cases}, Passed={run_b.passed_cases}, Failed={run_b.failed_cases}")

        results_a = db.scalars(
            select(CaseResult)
            .where(CaseResult.evaluation_run_id == run_a.id)
            .order_by(CaseResult.created_at.asc())
        ).all()
        results_b = db.scalars(
            select(CaseResult)
            .where(CaseResult.evaluation_run_id == run_b.id)
            .order_by(CaseResult.created_at.asc())
        ).all()

        print(f"\nRun A CaseResults: {len(results_a)}")
        print(f"Run B CaseResults: {len(results_b)}")

        print("\n--- PER-CASE BREAKDOWN FOR RUN A (v1 Good) ---")
        cases_with_missing_metrics = []
        total_metrics_a = 0
        for i, cr_a in enumerate(results_a):
            metrics_a = db.scalars(
                select(MetricResult).where(MetricResult.case_result_id == cr_a.id)
            ).all()
            total_metrics_a += len(metrics_a)
            metric_names = [m.metric_name for m in metrics_a]
            if len(metrics_a) != 3:
                cases_with_missing_metrics.append((i + 1, cr_a, metrics_a))
                print(f"Case {i+1} [ID: {cr_a.id}]: '{cr_a.test_case_snapshot.get('name')}'")
                print(f"  Status: {cr_a.status} | Latency: {cr_a.latency_ms}ms")
                print(f"  Error message: {cr_a.error_message}")
                print(f"  Metrics count: {len(metrics_a)} -> {metric_names}")
                for m in metrics_a:
                    print(f"    - {m.metric_name}: score={m.score}, passed={m.passed}, details={m.details}")

        total_metrics_b = 0
        for cr_b in results_b:
            metrics_b = db.scalars(
                select(MetricResult).where(MetricResult.case_result_id == cr_b.id)
            ).all()
            total_metrics_b += len(metrics_b)

        print(f"\nTotal Metrics persisted in Run A: {total_metrics_a}")
        print(f"Total Metrics persisted in Run B: {total_metrics_b}")
        print(f"Difference: {total_metrics_b - total_metrics_a} metrics missing in Run A!")

    finally:
        db.close()


if __name__ == "__main__":
    inspect_discrepancy()

