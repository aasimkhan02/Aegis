"""Unit and integration tests for the Evaluation Orchestrator and Evaluators."""

import unittest
import uuid

from sqlalchemy import select

from app.adapters.mock import MockAssistantAdapter
from app.db.session import SessionLocal
from app.evaluation.context import EvaluationContext, TestCaseData
from app.evaluation.evaluators.base import BaseEvaluator, EvaluatorResult
from app.evaluation.evaluators.expected_output import ExpectedOutputEvaluator
from app.evaluation.evaluators.response_presence import ResponsePresenceEvaluator
from app.evaluation.evaluators.tool_usage import ToolUsageEvaluator
from app.evaluation.exceptions import (
    AssistantResolutionError,
    EvaluationConfigError,
    IncompatibleProjectError,
)
from app.evaluation.executor import (
    build_conversation_request,
    create_test_case_snapshot,
    execute_test_case,
    resolve_assistant_adapter,
)
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
from app.schemas.adapter import AssistantResponse, ToolCall


class TestEvaluators(unittest.TestCase):
    """Test individual deterministic evaluators."""

    def test_response_presence_non_empty(self):
        evaluator = ResponsePresenceEvaluator()
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Test Presence",
            input_data={},
            actual_response=AssistantResponse(
                output="Valid response text",
                provider="mock",
                model="test-model",
                latency_ms=10,
            ),
        )
        res = evaluator.evaluate(context)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)
        self.assertEqual(res.metric_name, "response_presence")

    def test_response_presence_empty(self):
        evaluator = ResponsePresenceEvaluator()
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Test Empty",
            input_data={},
            actual_response=AssistantResponse(
                output="   ",
                provider="mock",
                model="test-model",
                latency_ms=10,
            ),
        )
        res = evaluator.evaluate(context)
        self.assertFalse(res.passed)
        self.assertEqual(res.score, 0.0)

    def test_expected_output_keywords_matching(self):
        evaluator = ExpectedOutputEvaluator(default_threshold=0.5)
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Keywords Test",
            input_data={},
            expected_output={"must_include": ["refrigerator", "inverter", "warranty", "340l"]},
            actual_response=AssistantResponse(
                output="The BharatHome refrigerator features a digital inverter compressor.",
                provider="mock",
                model="test-model",
                latency_ms=10,
            ),
        )
        res = evaluator.evaluate(context)
        # Matched: refrigerator, inverter (2 of 4 -> 0.5 ratio)
        self.assertEqual(res.score, 0.5)
        self.assertTrue(res.passed)
        self.assertEqual(len(res.details["matched"]), 2)
        self.assertEqual(len(res.details["missed"]), 2)

    def test_expected_output_exact_mode(self):
        evaluator = ExpectedOutputEvaluator()
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Exact Match Test",
            input_data={},
            expected_output={"exact": "Strict answer.", "match_type": "exact"},
            actual_response=AssistantResponse(
                output="Strict answer.",
                provider="mock",
                model="test-model",
                latency_ms=10,
            ),
        )
        res = evaluator.evaluate(context)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)

    def test_expected_output_non_applicable_without_assertions(self):
        evaluator = ExpectedOutputEvaluator()
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="No Assertion Test",
            input_data={},
            expected_output=None,
            actual_response=AssistantResponse(
                output="Some output.",
                provider="mock",
                model="test-model",
                latency_ms=10,
            ),
        )
        res = evaluator.evaluate(context)
        self.assertFalse(res.applicable)
        self.assertIn("No machine-readable expected output", res.details["reason"])

    def test_tool_usage_evaluator_matching(self):
        evaluator = ToolUsageEvaluator()
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Tool Matching Test",
            input_data={},
            metadata={"evaluation": {"expected_tools": ["product_lookup"]}},
            actual_response=AssistantResponse(
                output="Tool response",
                provider="mock",
                model="test-model",
                latency_ms=10,
                tool_calls=[ToolCall(name="product_lookup", arguments={})],
            ),
        )
        res = evaluator.evaluate(context)
        self.assertTrue(res.passed)
        self.assertEqual(res.score, 1.0)
        self.assertIn("product_lookup", res.details["matched"])

    def test_tool_usage_evaluator_missing_tool(self):
        evaluator = ToolUsageEvaluator()
        context = EvaluationContext(
            test_case_id=uuid.uuid4(),
            test_case_name="Missing Tool Test",
            input_data={},
            metadata={"evaluation": {"expected_tools": ["warranty_lookup"]}},
            actual_response=AssistantResponse(
                output="No tools called",
                provider="mock",
                model="test-model",
                latency_ms=10,
                tool_calls=[],
            ),
        )
        res = evaluator.evaluate(context)
        self.assertFalse(res.passed)
        self.assertEqual(res.score, 0.0)
        self.assertIn("warranty_lookup", res.details["missing"])


class TestEvaluationOrchestratorIntegration(unittest.IsolatedAsyncioTestCase):
    """Database integration tests for evaluation pipeline execution."""

    def setUp(self):
        self.db: Session = SessionLocal()
        suffix = uuid.uuid4().hex[:6]
        self.project = Project(name=f"Eval Test Proj {suffix}", slug=f"eval-proj-{suffix}")
        self.db.add(self.project)
        self.db.commit()

        self.dataset = Dataset(project_id=self.project.id, name=f"Eval Test Dataset {suffix}")
        self.assistant = AssistantVersion(
            project_id=self.project.id,
            name="Mock Test Assistant",
            version="1.0.0",
            provider="mock",
            model_name="mock-model",
            config={"simulated_latency_ms": 5},
        )
        self.db.add_all([self.dataset, self.assistant])
        self.db.commit()

        # Add 3 test cases: 2 enabled, 1 disabled
        self.tc1 = TestCase(
            dataset_id=self.dataset.id,
            name="Case 1: Accuracy Test",
            input_data={"messages": [{"role": "user", "content": "What is the difference between accuracy and reliability?"}]},
            expected_output={"must_include": ["accuracy", "reliability"]},
            is_enabled=True,
        )
        self.tc2 = TestCase(
            dataset_id=self.dataset.id,
            name="Case 2: Exact Match Test",
            input_data={"query": "ping"},
            expected_output={"must_include": ["pong"]},
            is_enabled=True,
        )
        self.tc3 = TestCase(
            dataset_id=self.dataset.id,
            name="Case 3: Disabled Case",
            input_data={"query": "ignore"},
            is_enabled=False,
        )
        self.db.add_all([self.tc1, self.tc2, self.tc3])
        self.db.commit()

    def tearDown(self):
        # Clean up in reverse FK order
        self.db.query(MetricResult).filter(
            MetricResult.case_result_id.in_(
                self.db.query(CaseResult.id).filter(
                    CaseResult.evaluation_run_id.in_(
                        self.db.query(EvaluationRun.id).filter(EvaluationRun.project_id == self.project.id)
                    )
                )
            )
        ).delete(synchronize_session=False)

        self.db.query(CaseResult).filter(
            CaseResult.evaluation_run_id.in_(
                self.db.query(EvaluationRun.id).filter(EvaluationRun.project_id == self.project.id)
            )
        ).delete(synchronize_session=False)

        self.db.query(EvaluationRun).filter(EvaluationRun.project_id == self.project.id).delete(synchronize_session=False)
        self.db.query(TestCase).filter(TestCase.dataset_id == self.dataset.id).delete(synchronize_session=False)
        self.db.query(Dataset).filter(Dataset.id == self.dataset.id).delete(synchronize_session=False)
        self.db.query(AssistantVersion).filter(AssistantVersion.id == self.assistant.id).delete(synchronize_session=False)
        self.db.query(Project).filter(Project.id == self.project.id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_validation_incompatible_project(self):
        other_proj = Project(name="Other Proj", slug=f"other-{uuid.uuid4().hex[:6]}")
        self.db.add(other_proj)
        self.db.commit()
        try:
            other_av = AssistantVersion(
                project_id=other_proj.id,
                name="Other Assistant",
                version="1.0.0",
                provider="mock",
                model_name="mock-model",
            )
            self.db.add(other_av)
            self.db.commit()

            with self.assertRaises(IncompatibleProjectError):
                validate_evaluation_entities(
                    self.db,
                    assistant_version_id=other_av.id,
                    dataset_id=self.dataset.id,
                )
        finally:
            self.db.query(AssistantVersion).filter(AssistantVersion.project_id == other_proj.id).delete()
            self.db.query(Project).filter(Project.id == other_proj.id).delete()
            self.db.commit()

    def test_validation_empty_dataset(self):
        empty_ds = Dataset(project_id=self.project.id, name="Empty DS")
        self.db.add(empty_ds)
        self.db.commit()
        try:
            with self.assertRaises(EvaluationConfigError):
                validate_evaluation_entities(
                    self.db,
                    assistant_version_id=self.assistant.id,
                    dataset_id=empty_ds.id,
                )
        finally:
            self.db.delete(empty_ds)
            self.db.commit()

    async def test_full_evaluation_lifecycle(self):
        # 1. Create evaluation run (pending)
        run = create_evaluation_run(
            db=self.db,
            assistant_version_id=self.assistant.id,
            dataset_id=self.dataset.id,
            config={"max_concurrency": 1},
        )
        self.assertEqual(run.status, "pending")
        self.assertEqual(run.total_cases, 2)  # Only the 2 enabled cases

        # 2. Execute evaluation run
        run_id = run.id
        await execute_evaluation_run(run_id, max_concurrency=1)

        # 3. Verify in a fresh database session
        fresh_db: Session = SessionLocal()
        try:
            completed_run = fresh_db.scalar(select(EvaluationRun).where(EvaluationRun.id == run_id))
            self.assertIsNotNone(completed_run)
            self.assertEqual(completed_run.status, "completed")
            self.assertEqual(completed_run.total_cases, 2)

            # Case results persisted
            results = fresh_db.scalars(
                select(CaseResult).where(CaseResult.evaluation_run_id == run_id)
            ).all()
            self.assertEqual(len(results), 2)

            # Check that counts reconcile
            passed = sum(1 for r in results if r.status == "passed")
            failed = sum(1 for r in results if r.status in ("failed", "error"))
            self.assertEqual(completed_run.passed_cases, passed)
            self.assertEqual(completed_run.failed_cases, failed)

            # Verify snapshot immutability
            for r in results:
                self.assertIn("input_data", r.test_case_snapshot)
                self.assertIsNotNone(r.actual_output)
                self.assertGreater(len(r.metric_results), 0)
        finally:
            fresh_db.close()


if __name__ == "__main__":
    unittest.main()
