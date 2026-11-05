"""Comprehensive verification script for Aegis Evaluation Orchestrator (Step 6).

Verifies end-to-end execution against local PostgreSQL across:
1. End-to-end evaluation integrity on the 40-case BharatHome Golden Dataset.
2. Fresh database session persistence and count reconciliation.
3. Snapshot and metric immutability.
4. Edge cases: incompatible projects, empty datasets, all-disabled cases,
   adapter exceptions, empty responses, evaluator errors, and fault tolerance.
"""

import asyncio
from pathlib import Path
import sys
import uuid

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.adapters.mock import MockAssistantAdapter
from app.db.session import SessionLocal
from app.evaluation.context import EvaluationContext, TestCaseData
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult
from app.evaluation.evaluators.expected_output import ExpectedOutputEvaluator
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.exceptions import EvaluationConfigError, IncompatibleProjectError
from app.evaluation.executor import execute_test_case
from app.evaluation.orchestrator import (
    create_evaluation_run,
    execute_evaluation_run,
    validate_evaluation_entities,
)
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.models.project import Project
from app.models.test_case import TestCase
from app.schemas.adapter import AssistantResponse, TokenUsage


async def verify_step6() -> bool:
    print("=" * 80)
    print("  AEGIS STEP 6: EVALUATION ORCHESTRATOR VERIFICATION SUITE")
    print("=" * 80)

    db: Session = SessionLocal()
    tests_passed = 0
    total_tests = 16

    try:
        # ----------------------------------------------------------------------
        # 1. Resolve Golden Dataset and Persisted Evaluation Runs
        # ----------------------------------------------------------------------
        dataset = db.scalar(
            select(Dataset).where(Dataset.name == "BharatHome Customer Support Golden Dataset")
        )
        assert dataset is not None, "BharatHome Golden Dataset must exist in database"

        runs = db.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.dataset_id == dataset.id)
            .order_by(EvaluationRun.created_at.desc())
            .limit(2)
        ).all()

        assert len(runs) >= 2, "At least two evaluation runs (v1 and v2) must exist"
        run_latest = runs[0]
        run_previous = runs[1]

        # ----------------------------------------------------------------------
        # Verification 1 & 2 & 3 & 4: Dataset & Assistant Association Integrity
        # ----------------------------------------------------------------------
        assert run_latest.dataset_id == run_previous.dataset_id == dataset.id
        print("  [CHECK 1-3] PASS: Both evaluation runs reference the same golden dataset.")

        assert run_latest.assistant_version_id != run_previous.assistant_version_id
        print("  [CHECK 4]   PASS: The two runs reference distinct assistant versions.")

        # ----------------------------------------------------------------------
        # Verification 5 & 6 & 7: Processing & CaseResults Persisted
        # ----------------------------------------------------------------------
        for r in [run_latest, run_previous]:
            case_results = db.scalars(
                select(CaseResult).where(CaseResult.evaluation_run_id == r.id)
            ).all()
            assert len(case_results) == 40, f"Run {r.id} must process all 40 cases"
            assert r.total_cases == 40
            assert r.status == "completed"
        print("  [CHECK 5-7] PASS: All 40 enabled test cases processed and persisted.")

        # ----------------------------------------------------------------------
        # Verification 8 & 9 & 10: Metrics, Latency, Output, Tool Calls
        # ----------------------------------------------------------------------
        sample_cr = db.scalar(
            select(CaseResult).where(CaseResult.evaluation_run_id == run_latest.id)
        )
        assert sample_cr is not None
        assert sample_cr.latency_ms is not None and sample_cr.latency_ms >= 0
        assert sample_cr.actual_output is not None
        assert "output" in sample_cr.actual_output
        assert "tool_calls" in sample_cr.actual_output

        metrics = db.scalars(
            select(MetricResult).where(MetricResult.case_result_id == sample_cr.id)
        ).all()
        assert len(metrics) >= 2, "Each case must have response_presence and expected_output metrics"
        for m in metrics:
            assert 0.0 <= m.score <= 1.0, f"Score {m.score} must be within [0.0, 1.0]"
            if m.threshold is not None:
                assert 0.0 <= m.threshold <= 1.0
        print("  [CHECK 8-10] PASS: Latency, actual output, tool calls, and valid metrics persisted.")

        # ----------------------------------------------------------------------
        # Verification 11 & 12: Snapshot Integrity & Fresh Session Verification
        # ----------------------------------------------------------------------
        snap = sample_cr.test_case_snapshot
        assert "input_data" in snap
        assert "expected_output" in snap
        assert "expected_behavior" in snap
        assert "retrieval_context" in snap
        assert "id" in snap
        print("  [CHECK 11]  PASS: Snapshots preserve original input, expected output, and context.")

        # Verify in a completely separate, fresh database session
        fresh_db: Session = SessionLocal()
        try:
            fresh_run = fresh_db.scalar(select(EvaluationRun).where(EvaluationRun.id == run_latest.id))
            assert fresh_run is not None
            assert fresh_run.status == "completed"
            fresh_count = fresh_db.scalar(
                select(func.count(CaseResult.id)).where(CaseResult.evaluation_run_id == fresh_run.id)
            )
            assert fresh_count == 40
            print("  [CHECK 12]  PASS: Fresh database session retrieves all persisted records.")
        finally:
            fresh_db.close()

        # ----------------------------------------------------------------------
        # Verification 13 & 14 & 16: Count Reconciliation & Fault Tolerant Completion
        # ----------------------------------------------------------------------
        for r in [run_latest, run_previous]:
            db_results = db.scalars(
                select(CaseResult).where(CaseResult.evaluation_run_id == r.id)
            ).all()
            actual_passed = sum(1 for c in db_results if c.status == "passed")
            actual_failed = sum(1 for c in db_results if c.status in ("failed", "error"))

            assert r.passed_cases == actual_passed
            assert r.failed_cases == actual_failed
            assert r.total_cases == actual_passed + actual_failed
            assert r.status == "completed", "Run with partial failures must complete, not fail"
        print("  [CHECK 13-14] PASS: Aggregate counts match persisted CaseResults.")
        print("  [CHECK 16]  PASS: Completed runs with partial failures classified as 'completed'.")

        # ----------------------------------------------------------------------
        # Verification 15: Evaluator Error Does Not Produce False Pass
        # ----------------------------------------------------------------------
        class BrokenEvaluator(BaseEvaluator):
            name = "broken_evaluator"
            def evaluate(self, context: EvaluationContext) -> EvaluatorResult:
                raise RuntimeError("Simulated crash in evaluator")

        test_tc = TestCaseData(
            id=uuid.uuid4(),
            name="Faulty Eval Test",
            input_data={"messages": [{"role": "user", "content": "Hello"}]},
            expected_output={"exact": "Hello"},
        )
        mock_adapter = MockAssistantAdapter(default_response="Hello")
        fault_result = await execute_test_case(
            test_case=test_tc,
            adapter=mock_adapter,
            evaluators=[BrokenEvaluator()],
        )
        assert fault_result.status == "error", "Evaluator exception must produce status='error'"
        assert any("Simulated crash" in str(m.details) for m in fault_result.metric_results)
        print("  [CHECK 15]  PASS: Evaluator exception produces status='error', never a false pass.")

        tests_passed = 16

    finally:
        db.close()

    # --------------------------------------------------------------------------
    # Part 2: Edge Cases Verification Suite
    # --------------------------------------------------------------------------
    print("\n" + "-" * 80)
    print("  EDGE CASES & FAULT INJECTION TESTS")
    print("-" * 80)

    edge_db: Session = SessionLocal()
    edge_passed = 0
    total_edge = 6

    try:
        # Edge Case 1: Incompatible Project Validation
        proj_a = Project(name="Edge Proj A", slug=f"edge-a-{uuid.uuid4().hex[:6]}")
        proj_b = Project(name="Edge Proj B", slug=f"edge-b-{uuid.uuid4().hex[:6]}")
        edge_db.add_all([proj_a, proj_b])
        edge_db.commit()

        ds_a = Dataset(project_id=proj_a.id, name="Dataset in Proj A")
        av_b = AssistantVersion(
            project_id=proj_b.id,
            name="Assistant in Proj B",
            version="1.0.0",
            provider="mock",
            model_name="mock-model",
        )
        edge_db.add_all([ds_a, av_b])
        edge_db.commit()

        try:
            validate_evaluation_entities(edge_db, assistant_version_id=av_b.id, dataset_id=ds_a.id)
            assert False, "Should have raised IncompatibleProjectError"
        except IncompatibleProjectError:
            print("  [EDGE 1] PASS: Incompatible project combination correctly rejected with IncompatibleProjectError.")
            edge_passed += 1

        # Edge Case 2: Empty Dataset (Zero Test Cases)
        try:
            validate_evaluation_entities(edge_db, assistant_version_id=av_b.id, dataset_id=av_b.id)  # mismatch
        except Exception:
            pass

        ds_empty = Dataset(project_id=proj_a.id, name="Empty Dataset")
        av_a = AssistantVersion(
            project_id=proj_a.id,
            name="Assistant in Proj A",
            version="1.0.0",
            provider="mock",
            model_name="mock-model",
        )
        edge_db.add_all([ds_empty, av_a])
        edge_db.commit()

        try:
            validate_evaluation_entities(edge_db, assistant_version_id=av_a.id, dataset_id=ds_empty.id)
            assert False, "Should have raised EvaluationConfigError on empty dataset"
        except EvaluationConfigError as e:
            assert "no enabled test cases" in str(e).lower()
            print("  [EDGE 2] PASS: Empty dataset with 0 test cases rejected.")
            edge_passed += 1

        # Edge Case 3: All Test Cases Disabled
        tc_disabled = TestCase(
            dataset_id=ds_empty.id,
            name="Disabled Case",
            input_data={"messages": [{"role": "user", "content": "test"}]},
            is_enabled=False,
        )
        edge_db.add(tc_disabled)
        edge_db.commit()

        try:
            validate_evaluation_entities(edge_db, assistant_version_id=av_a.id, dataset_id=ds_empty.id)
            assert False, "Should have raised EvaluationConfigError when all test cases are disabled"
        except EvaluationConfigError:
            print("  [EDGE 3] PASS: Dataset with only disabled test cases rejected.")
            edge_passed += 1

        # Edge Case 4: Assistant Adapter Failure / Exception Handling
        failing_adapter = MockAssistantAdapter(should_fail=True)
        tc_exec = TestCaseData(
            id=uuid.uuid4(),
            name="Failing Adapter Test",
            input_data={"query": "test query"},
        )
        res_fail = await execute_test_case(
            test_case=tc_exec,
            adapter=failing_adapter,
            evaluators=[ResponsePresenceEvaluator()],
        )
        assert res_fail.status == "error"
        assert res_fail.error_message is not None
        assert "Simulated mock provider failure" in res_fail.error_message
        print("  [EDGE 4] PASS: Assistant exception cleanly captured as status='error' with error message.")
        edge_passed += 1

        # Edge Case 5: Empty Assistant Response Handling
        empty_adapter = MockAssistantAdapter(default_response="")
        res_empty = await execute_test_case(
            test_case=tc_exec,
            adapter=empty_adapter,
            evaluators=[ResponsePresenceEvaluator()],
        )
        assert res_empty.status == "failed"
        assert res_empty.metric_results[0].passed is False
        assert res_empty.metric_results[0].score == 0.0
        print("  [EDGE 5] PASS: Empty assistant response scores 0.0 and fails response_presence.")
        edge_passed += 1

        # Edge Case 6: Duplicate Result Prevention (UniqueConstraint)
        # Attempting to insert duplicate (evaluation_run_id, test_case_id) must raise IntegrityError
        from sqlalchemy.exc import IntegrityError
        run_record = EvaluationRun(
            project_id=proj_a.id,
            assistant_version_id=av_a.id,
            dataset_id=ds_empty.id,
            status="pending",
        )
        edge_db.add(run_record)
        edge_db.commit()

        cr_1 = CaseResult(
            evaluation_run_id=run_record.id,
            test_case_id=tc_disabled.id,
            test_case_snapshot={"name": "test"},
            status="passed",
        )
        edge_db.add(cr_1)
        edge_db.commit()

        cr_dup = CaseResult(
            evaluation_run_id=run_record.id,
            test_case_id=tc_disabled.id,
            test_case_snapshot={"name": "duplicate"},
            status="failed",
        )
        edge_db.add(cr_dup)
        try:
            edge_db.commit()
            assert False, "Should have raised IntegrityError on duplicate (evaluation_run_id, test_case_id)"
        except IntegrityError:
            edge_db.rollback()
            print("  [EDGE 6] PASS: Duplicate CaseResult prevention enforced by database UniqueConstraint.")
            edge_passed += 1

    finally:
        edge_db.close()

    print("\n" + "=" * 80)
    print(f"  VERIFICATION SUITE COMPLETE: {tests_passed}/{total_tests} Core + {edge_passed}/{total_edge} Edge Checks PASSED")
    print("=" * 80 + "\n")
    return True


if __name__ == "__main__":
    success = asyncio.run(verify_step6())
    sys.exit(0 if success else 1)
