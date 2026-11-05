"""Integration tests against PostgreSQL verifying constraints, relationships, JSONB, and history preservation."""

from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import unittest
import uuid

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.project import Project
from app.models.assistant_version import AssistantVersion
from app.models.dataset import Dataset
from app.models.test_case import TestCase
from app.models.evaluation_run import EvaluationRun
from app.models.case_result import CaseResult
from app.models.metric_result import MetricResult


class TestDatabaseIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not settings.database_url:
            raise unittest.SkipTest("DATABASE_URL not set; skipping PostgreSQL integration tests.")
        cls.engine = create_engine(settings.database_url, pool_pre_ping=True)
        cls.SessionFactory = sessionmaker(bind=cls.engine, autoflush=False, autocommit=False)

    def setUp(self):
        self.session: Session = self.SessionFactory()
        self.suffix = uuid.uuid4().hex[:8]

    def tearDown(self):
        self.session.rollback()
        self.session.close()

    def _create_base_hierarchy(self):
        """Helper to create project, assistant version, dataset, testcase."""
        project = Project(
            name=f"Test Project {self.suffix}",
            slug=f"test-proj-{self.suffix}",
            description="Integration test project",
        )
        self.session.add(project)
        self.session.flush()

        av = AssistantVersion(
            project_id=project.id,
            name="Test Assistant",
            version="1.0.0",
            provider="anthropic",
            model_name="claude-3-5-sonnet",
            system_prompt="Test system prompt",
            config={"temperature": 0.5},
        )
        self.session.add(av)

        dataset = Dataset(
            project_id=project.id,
            name=f"Dataset {self.suffix}",
            description="Test dataset",
            metadata={"domain": "safety"},
        )
        self.session.add(dataset)
        self.session.flush()

        tc = TestCase(
            dataset_id=dataset.id,
            name="Sample Test Case",
            input_data={"messages": [{"role": "user", "content": "Hello"}]},
            expected_output={"response": "Hi there!"},
            expected_behavior="Polite greeting",
            tags=["greeting", "basic"],
            metadata={"priority": "high"},
        )
        self.session.add(tc)
        self.session.flush()

        return project, av, dataset, tc

    def test_model_creation_and_relationships(self):
        """Test full hierarchy creation, foreign keys, and relationships navigation."""
        project, av, dataset, tc = self._create_base_hierarchy()

        eval_run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="pending",
            config={"max_parallel": 2},
            total_cases=1,
            passed_cases=0,
            failed_cases=0,
        )
        self.session.add(eval_run)
        self.session.flush()

        case_res = CaseResult(
            evaluation_run_id=eval_run.id,
            test_case_id=tc.id,
            test_case_snapshot={"input": tc.input_data, "expected": tc.expected_behavior},
            status="passed",
            latency_ms=150,
        )
        self.session.add(case_res)
        self.session.flush()

        metric = MetricResult(
            case_result_id=case_res.id,
            metric_name="correctness",
            score=0.95,
            threshold=0.8,
            passed=True,
            details={"notes": "good response"},
        )
        self.session.add(metric)
        self.session.commit()

        # Query back and verify back-population
        fetched_run = self.session.get(EvaluationRun, eval_run.id)
        self.assertIsNotNone(fetched_run)
        self.assertEqual(fetched_run.project.id, project.id)
        self.assertEqual(fetched_run.assistant_version.id, av.id)
        self.assertEqual(fetched_run.dataset.id, dataset.id)
        self.assertEqual(len(fetched_run.case_results), 1)
        self.assertEqual(fetched_run.case_results[0].id, case_res.id)
        self.assertEqual(len(fetched_run.case_results[0].metric_results), 1)
        self.assertEqual(fetched_run.case_results[0].metric_results[0].score, 0.95)

    def test_unique_constraint_project_slug(self):
        """Projects with duplicate slugs must violate unique constraint."""
        slug = f"unique-slug-{self.suffix}"
        p1 = Project(name="P1", slug=slug)
        p2 = Project(name="P2", slug=slug)
        self.session.add(p1)
        self.session.commit()

        self.session.add(p2)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_unique_constraint_assistant_version(self):
        """AssistantVersion with duplicate (project_id, version) must violate unique constraint."""
        project, _, _, _ = self._create_base_hierarchy()
        av1 = AssistantVersion(
            project_id=project.id,
            name="A1",
            version="2.0.0",
        )
        av2 = AssistantVersion(
            project_id=project.id,
            name="A2",
            version="2.0.0",
        )
        self.session.add(av1)
        self.session.commit()

        self.session.add(av2)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_unique_constraint_case_result(self):
        """CaseResult with duplicate (evaluation_run_id, test_case_id) must be rejected."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="running",
        )
        self.session.add(run)
        self.session.flush()

        cr1 = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={"name": "test"},
            status="passed",
        )
        cr2 = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={"name": "test"},
            status="failed",
        )
        self.session.add(cr1)
        self.session.commit()

        self.session.add(cr2)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_unique_constraint_metric_result(self):
        """Duplicate metric_name for the same case_result_id must be rejected."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="running",
        )
        self.session.add(run)
        self.session.flush()

        cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={"name": "test"},
            status="passed",
        )
        self.session.add(cr)
        self.session.flush()

        m1 = MetricResult(
            case_result_id=cr.id,
            metric_name="faithfulness",
            score=0.9,
            passed=True,
        )
        m2 = MetricResult(
            case_result_id=cr.id,
            metric_name="faithfulness",
            score=0.7,
            passed=False,
        )
        self.session.add(m1)
        self.session.commit()

        self.session.add(m2)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_invalid_evaluation_run_status_rejected(self):
        """EvaluationRun status outside allowed set must violate CHECK constraint."""
        project, av, dataset, _ = self._create_base_hierarchy()
        invalid_run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="not_a_valid_status",
        )
        self.session.add(invalid_run)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_negative_evaluation_run_case_counts_rejected(self):
        """Negative case counts on EvaluationRun must violate CHECK constraint."""
        project, av, dataset, _ = self._create_base_hierarchy()
        invalid_run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="pending",
            total_cases=-5,
        )
        self.session.add(invalid_run)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_invalid_case_result_status_rejected(self):
        """CaseResult status outside ('passed', 'failed', 'error', 'skipped') must violate CHECK constraint."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="running",
        )
        self.session.add(run)
        self.session.flush()

        invalid_cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={},
            status="in_progress",  # invalid
        )
        self.session.add(invalid_cr)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_negative_case_result_latency_rejected(self):
        """Negative latency_ms must violate CHECK constraint."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="running",
        )
        self.session.add(run)
        self.session.flush()

        invalid_cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={},
            status="passed",
            latency_ms=-1,
        )
        self.session.add(invalid_cr)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_invalid_metric_score_rejected(self):
        """MetricResult score > 1.0 or < 0.0 must violate CHECK constraint."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="running",
        )
        self.session.add(run)
        self.session.flush()

        cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={},
            status="passed",
        )
        self.session.add(cr)
        self.session.flush()

        invalid_metric = MetricResult(
            case_result_id=cr.id,
            metric_name="safety",
            score=1.2,  # out of bounds (> 1.0)
            passed=True,
        )
        self.session.add(invalid_metric)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_invalid_metric_threshold_rejected(self):
        """MetricResult threshold > 1.0 or < 0.0 must violate CHECK constraint."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="running",
        )
        self.session.add(run)
        self.session.flush()

        cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={},
            status="passed",
        )
        self.session.add(cr)
        self.session.flush()

        invalid_metric = MetricResult(
            case_result_id=cr.id,
            metric_name="safety",
            score=0.9,
            threshold=-0.1,  # out of bounds (< 0.0)
            passed=True,
        )
        self.session.add(invalid_metric)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_evaluation_history_preservation_restrict(self):
        """Deleting an EvaluationRun when it has CaseResults must fail due to RESTRICT ondelete."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="completed",
        )
        self.session.add(run)
        self.session.flush()

        cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={"original": "snapshot"},
            status="passed",
        )
        self.session.add(cr)
        self.session.commit()

        # Attempting to delete the EvaluationRun directly must be prevented by RESTRICT
        self.session.delete(run)
        with self.assertRaises(IntegrityError):
            self.session.commit()

    def test_historical_snapshot_preservation_after_test_case_update(self):
        """CaseResult.test_case_snapshot must remain untouched even if the TestCase is modified."""
        project, av, dataset, tc = self._create_base_hierarchy()
        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="completed",
        )
        self.session.add(run)
        self.session.flush()

        initial_snapshot = {
            "name": tc.name,
            "input_data": tc.input_data,
            "expected_behavior": tc.expected_behavior,
        }
        cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot=initial_snapshot,
            status="passed",
        )
        self.session.add(cr)
        self.session.commit()

        # Now edit the test case in place
        tc.name = "Completely Altered Name"
        tc.expected_behavior = "Completely altered expected behavior"
        tc.input_data = {"messages": [{"role": "user", "content": "Modified input"}]}
        self.session.commit()

        # Re-fetch CaseResult in fresh session check
        fresh_session: Session = self.SessionFactory()
        try:
            fetched_cr = fresh_session.get(CaseResult, cr.id)
            self.assertEqual(fetched_cr.test_case_snapshot, initial_snapshot)
            self.assertNotEqual(fetched_cr.test_case.name, fetched_cr.test_case_snapshot["name"])
        finally:
            fresh_session.close()


if __name__ == "__main__":
    unittest.main()

