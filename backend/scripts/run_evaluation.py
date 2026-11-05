"""Run end-to-end evaluation runs against the local PostgreSQL database.

Executes the 40-case BharatHome Golden Dataset against:
- Run A: BharatHome Assistant v1 (Production / Good)
- Run B: BharatHome Assistant v2 (Intentionally Broken)
"""

import asyncio
from pathlib import Path
import sys
import time

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.evaluation.orchestrator import create_evaluation_run, execute_evaluation_run
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult


async def run_end_to_end_evaluations() -> tuple[EvaluationRun, EvaluationRun]:
    print("=" * 80)
    print("  AEGIS STEP 6: END-TO-END EVALUATION RUN PIPELINE")
    print("=" * 80)

    db: Session = SessionLocal()
    try:
        # 1. Resolve Golden Dataset
        dataset = db.scalar(
            select(Dataset).where(Dataset.name == "BharatHome Customer Support Golden Dataset")
        )
        if not dataset:
            print("[FAIL] 'BharatHome Customer Support Golden Dataset' not found in database.")
            sys.exit(1)

        # 2. Resolve Assistants v1 and v2
        v1 = db.scalar(
            select(AssistantVersion).where(
                AssistantVersion.project_id == dataset.project_id,
                AssistantVersion.version == "v1.0.0-good",
            )
        )
        v2 = db.scalar(
            select(AssistantVersion).where(
                AssistantVersion.project_id == dataset.project_id,
                AssistantVersion.version == "v2.0.0-broken",
            )
        )

        if not v1 or not v2:
            print(f"[FAIL] BharatHome assistant versions not found in project '{dataset.project_id}'.")
            sys.exit(1)

        print(f"[INFO] Project ID: {dataset.project_id}")
        print(f"[INFO] Golden Dataset: '{dataset.name}' (ID: {dataset.id})")
        print(f"[INFO] Assistant v1 (Good): '{v1.name}' (ID: {v1.id})")
        print(f"[INFO] Assistant v2 (Broken): '{v2.name}' (ID: {v2.id})\n")

        # ----------------------------------------------------------------------
        # RUN A: BharatHome Assistant v1 (Good)
        # ----------------------------------------------------------------------
        print("-" * 80)
        print("  INITIATING RUN A: BharatHome Assistant v1 (Production)")
        print("-" * 80)
        run_v1 = create_evaluation_run(
            db=db,
            assistant_version_id=v1.id,
            dataset_id=dataset.id,
            config={"max_concurrency": 1, "fail_fast": False, "mode": "e2e_verification"},
        )
        run_v1_id = run_v1.id
        total_cases_v1 = run_v1.total_cases
        print(f"[CREATED] EvaluationRun A: ID={run_v1_id}, Cases={total_cases_v1}")

        t0_v1 = time.perf_counter()
        await execute_evaluation_run(run_v1_id, max_concurrency=1, fail_fast=False)
        duration_v1 = time.perf_counter() - t0_v1
        print(f"[COMPLETED] EvaluationRun A in {duration_v1:.2f}s")

        # ----------------------------------------------------------------------
        # RUN B: BharatHome Assistant v2 (Broken)
        # ----------------------------------------------------------------------
        print("\n" + "-" * 80)
        print("  INITIATING RUN B: BharatHome Assistant v2 (Intentionally Broken)")
        print("-" * 80)
        run_v2 = create_evaluation_run(
            db=db,
            assistant_version_id=v2.id,
            dataset_id=dataset.id,
            config={"max_concurrency": 1, "fail_fast": False, "mode": "e2e_verification"},
        )
        run_v2_id = run_v2.id
        total_cases_v2 = run_v2.total_cases
        print(f"[CREATED] EvaluationRun B: ID={run_v2_id}, Cases={total_cases_v2}")

        t0_v2 = time.perf_counter()
        await execute_evaluation_run(run_v2_id, max_concurrency=1, fail_fast=False)
        duration_v2 = time.perf_counter() - t0_v2
        print(f"[COMPLETED] EvaluationRun B in {duration_v2:.2f}s")

    finally:
        db.close()

    # --------------------------------------------------------------------------
    # Inspect Persisted Results from a Fresh Database Session
    # --------------------------------------------------------------------------
    inspect_db: Session = SessionLocal()
    try:
        final_v1 = inspect_db.scalar(select(EvaluationRun).where(EvaluationRun.id == run_v1_id))
        final_v2 = inspect_db.scalar(select(EvaluationRun).where(EvaluationRun.id == run_v2_id))

        results_v1 = inspect_db.scalars(
            select(CaseResult).where(CaseResult.evaluation_run_id == run_v1_id)
        ).all()
        results_v2 = inspect_db.scalars(
            select(CaseResult).where(CaseResult.evaluation_run_id == run_v2_id)
        ).all()

        metrics_count_v1 = inspect_db.scalar(
            select(func.count(MetricResult.id))
            .join(CaseResult, MetricResult.case_result_id == CaseResult.id)
            .where(CaseResult.evaluation_run_id == run_v1_id)
        )
        metrics_count_v2 = inspect_db.scalar(
            select(func.count(MetricResult.id))
            .join(CaseResult, MetricResult.case_result_id == CaseResult.id)
            .where(CaseResult.evaluation_run_id == run_v2_id)
        )

        print("\n" + "=" * 80)
        print("  EVALUATION COMPARISON SUMMARY (FRESH DATABASE SESSION)")
        print("=" * 80)
        print(f"{'Metric':<30} | {'Run A (v1 Good)':<22} | {'Run B (v2 Broken)':<22}")
        print("-" * 80)
        print(f"{'Run ID':<30} | {str(final_v1.id)[:20]:<22} | {str(final_v2.id)[:20]:<22}")
        print(f"{'Status':<30} | {final_v1.status:<22} | {final_v2.status:<22}")
        print(f"{'Total Cases':<30} | {final_v1.total_cases:<22} | {final_v2.total_cases:<22}")
        print(f"{'Passed Cases':<30} | {final_v1.passed_cases:<22} | {final_v2.passed_cases:<22}")
        print(f"{'Failed Cases':<30} | {final_v1.failed_cases:<22} | {final_v2.failed_cases:<22}")
        v1_rate = (final_v1.passed_cases / final_v1.total_cases * 100) if final_v1.total_cases else 0
        v2_rate = (final_v2.passed_cases / final_v2.total_cases * 100) if final_v2.total_cases else 0
        print(f"{'Pass Rate':<30} | {v1_rate:>6.1f}%{'':<15} | {v2_rate:>6.1f}%{'':<15}")
        print(f"{'Persisted CaseResults':<30} | {len(results_v1):<22} | {len(results_v2):<22}")
        print(f"{'Persisted MetricResults':<30} | {metrics_count_v1:<22} | {metrics_count_v2:<22}")
        print(f"{'Execution Duration':<30} | {duration_v1:>6.2f}s{'':<15} | {duration_v2:>6.2f}s{'':<15}")
        print("-" * 80)

        # Show Sample Divergent Results
        print("\n[SAMPLE CASE RESULTS INSPECTION]")
        sample_cases = [1, 2, 6, 7]  # Specs, Warranty, Microwave Bypass, Service Request
        for idx in sample_cases:
            if idx <= len(results_v1) and idx <= len(results_v2):
                c1 = results_v1[idx - 1]
                c2 = results_v2[idx - 1]
                q_name = c1.test_case_snapshot.get("name", f"Case {idx}")
                print(f"  Case {idx}: {q_name}")
                print(f"    v1 (Good):   Status = {c1.status:<7} | Latency = {c1.latency_ms}ms")
                print(f"    v2 (Broken): Status = {c2.status:<7} | Latency = {c2.latency_ms}ms | Flaw = {c2.actual_output.get('metadata', {}).get('evaluation_flaw_injected', 'None')}")

        print("\n[SUCCESS] End-to-end evaluation pipeline completed successfully!")
        return final_v1, final_v2
    finally:
        inspect_db.close()


if __name__ == "__main__":
    asyncio.run(run_end_to_end_evaluations())
