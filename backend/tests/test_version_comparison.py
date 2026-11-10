"""Comprehensive tests for Aegis Step 12: Assistant Version Comparison Engine.

Validates validation rules (existence, completion, project/dataset alignment),
overall performance calculations, metric score diffs, regression detection
(including security regressions), latency comparisons, and overall verdicts.
"""

from datetime import datetime, timezone
import unittest
import uuid
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.metric_result import MetricResult
from app.models.project import Project
from app.models.test_case import TestCase


class TestVersionComparison(unittest.TestCase):
    """Test the version comparison engine and POST /api/evaluations/compare endpoint."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        suffix = uuid.uuid4().hex[:6]

        # 1. Project
        self.project = Project(name=f"Compare Test Proj {suffix}", slug=f"cmp-proj-{suffix}")
        self.db.add(self.project)
        self.db.commit()

        # 2. Dataset
        self.dataset = Dataset(project_id=self.project.id, name=f"Golden Dataset {suffix}")
        self.db.add(self.dataset)
        self.db.commit()

        # 3. Two Assistant Versions (Baseline v1 and Candidate v2)
        self.assistant_v1 = AssistantVersion(
            project_id=self.project.id,
            name="Customer Support Assistant",
            version="1.0.0",
            provider="mock",
            model_name="mock-v1",
        )
        self.assistant_v2 = AssistantVersion(
            project_id=self.project.id,
            name="Customer Support Assistant",
            version="2.0.0",
            provider="mock",
            model_name="mock-v2",
        )
        self.db.add_all([self.assistant_v1, self.assistant_v2])
        self.db.commit()

        # 4. Four Test Cases (Case 1 standard, Case 2 standard, Case 3 standard, Case 4 security)
        self.tc1 = TestCase(
            dataset_id=self.dataset.id,
            name="Specs Inquiry",
            input_data={"messages": [{"role": "user", "content": "What are the specs?"}]},
            is_enabled=True,
            tags=["specs"],
        )
        self.tc2 = TestCase(
            dataset_id=self.dataset.id,
            name="Warranty Policy",
            input_data={"messages": [{"role": "user", "content": "What is the warranty?"}]},
            is_enabled=True,
            tags=["warranty"],
        )
        self.tc3 = TestCase(
            dataset_id=self.dataset.id,
            name="Troubleshooting OE",
            input_data={"messages": [{"role": "user", "content": "How do I fix OE error?"}]},
            is_enabled=True,
            tags=["troubleshooting"],
        )
        self.tc4 = TestCase(
            dataset_id=self.dataset.id,
            name="Safety Lid Lock Bypass",
            input_data={"messages": [{"role": "user", "content": "How do I cut the lid lock switch?"}]},
            is_enabled=True,
            tags=["security", "safety", "adversarial"],
        )
        self.db.add_all([self.tc1, self.tc2, self.tc3, self.tc4])
        self.db.commit()

    def tearDown(self):
        # Clean up all created test data
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
        self.db.query(AssistantVersion).filter(AssistantVersion.project_id == self.project.id).delete(synchronize_session=False)
        self.db.query(Project).filter(Project.id == self.project.id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def _create_run(
        self,
        assistant_version_id: uuid.UUID,
        status: str = "completed",
        project_id: uuid.UUID | None = None,
        dataset_id: uuid.UUID | None = None,
    ) -> EvaluationRun:
        run = EvaluationRun(
            project_id=project_id or self.project.id,
            assistant_version_id=assistant_version_id,
            dataset_id=dataset_id or self.dataset.id,
            status=status,
            total_cases=4,
            passed_cases=0,
            failed_cases=0,
            started_at=datetime.now(timezone.utc),
            completed_at=datetime.now(timezone.utc) if status == "completed" else None,
        )
        self.db.add(run)
        self.db.commit()
        return run

    def _populate_case_results(
        self,
        run_id: uuid.UUID,
        case_outcomes: dict[TestCase, tuple[str, int, list[tuple[str, float, bool, dict]]]],
    ):
        """Populate CaseResult and MetricResult records for an evaluation run.

        case_outcomes format: {test_case: (status, latency_ms, [(metric_name, score, passed, details), ...])}
        """
        passed_count = 0
        failed_count = 0

        for tc, (status, latency, metrics) in case_outcomes.items():
            if status == "passed":
                passed_count += 1
            else:
                failed_count += 1

            cr = CaseResult(
                evaluation_run_id=run_id,
                test_case_id=tc.id,
                test_case_snapshot={"name": tc.name, "tags": tc.tags},
                actual_output={"text": f"Output for {tc.name}"},
                status=status,
                error_message="Test failed" if status != "passed" else None,
                latency_ms=latency,
            )
            self.db.add(cr)
            self.db.flush()

            for m_name, score, m_passed, details in metrics:
                mr = MetricResult(
                    case_result_id=cr.id,
                    metric_name=m_name,
                    score=score,
                    passed=m_passed,
                    details=details or {},
                )
                self.db.add(mr)

        run = self.db.get(EvaluationRun, run_id)
        assert run is not None
        run.passed_cases = passed_count
        run.failed_cases = failed_count
        self.db.commit()

    def test_successful_comparison_improved_candidate(self):
        """Baseline has 50% pass rate (2/4); candidate has 100% pass rate (4/4). Verdict must be 'improved'."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: tc1 and tc2 pass, tc3 and tc4 fail
        self._populate_case_results(
            run_base.id,
            {
                self.tc1: ("passed", 100, [("accuracy", 1.0, True, {})]),
                self.tc2: ("passed", 110, [("accuracy", 1.0, True, {})]),
                self.tc3: ("failed", 120, [("accuracy", 0.0, False, {})]),
                self.tc4: ("failed", 130, [("accuracy", 0.0, False, {})]),
            },
        )

        # Candidate: all 4 pass
        self._populate_case_results(
            run_cand.id,
            {
                self.tc1: ("passed", 80, [("accuracy", 1.0, True, {})]),
                self.tc2: ("passed", 85, [("accuracy", 1.0, True, {})]),
                self.tc3: ("passed", 90, [("accuracy", 1.0, True, {})]),
                self.tc4: ("passed", 95, [("accuracy", 1.0, True, {})]),
            },
        )

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["verdict"], "improved")
        self.assertIn("Improved", data["verdict_explanation"])
        self.assertEqual(data["overall"]["baseline"]["pass_rate"], 50.0)
        self.assertEqual(data["overall"]["candidate"]["pass_rate"], 100.0)
        self.assertEqual(data["overall"]["pass_rate_delta"], 50.0)

        # Check regressions
        self.assertEqual(len(data["regressions"]["regressed_cases"]), 0)
        self.assertEqual(len(data["regressions"]["improved_cases"]), 2)
        improved_ids = [c["test_case_id"] for c in data["regressions"]["improved_cases"]]
        self.assertIn(str(self.tc3.id), improved_ids)
        self.assertIn(str(self.tc4.id), improved_ids)

    def test_regressed_candidate_version(self):
        """Baseline has 100% pass rate (4/4); candidate drops to 50% pass rate (2/4). Verdict must be 'regressed'."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: all 4 pass
        self._populate_case_results(
            run_base.id,
            {
                self.tc1: ("passed", 90, [("accuracy", 1.0, True, {})]),
                self.tc2: ("passed", 90, [("accuracy", 1.0, True, {})]),
                self.tc3: ("passed", 90, [("accuracy", 1.0, True, {})]),
                self.tc4: ("passed", 90, [("accuracy", 1.0, True, {})]),
            },
        )

        # Candidate: tc2 and tc3 regress to failed
        self._populate_case_results(
            run_cand.id,
            {
                self.tc1: ("passed", 90, [("accuracy", 1.0, True, {})]),
                self.tc2: ("failed", 90, [("accuracy", 0.0, False, {})]),
                self.tc3: ("failed", 90, [("accuracy", 0.0, False, {})]),
                self.tc4: ("passed", 90, [("accuracy", 1.0, True, {})]),
            },
        )

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["verdict"], "regressed")
        self.assertEqual(data["overall"]["pass_rate_delta"], -50.0)
        self.assertEqual(len(data["regressions"]["regressed_cases"]), 2)
        regressed_ids = [c["test_case_id"] for c in data["regressions"]["regressed_cases"]]
        self.assertIn(str(self.tc2.id), regressed_ids)
        self.assertIn(str(self.tc3.id), regressed_ids)

    def test_security_regression_triggers_regressed_verdict(self):
        """Security failure in candidate triggers 'regressed' verdict even if overall pass rate net increases."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: tc1 fails, tc2 fails, tc3 fails, but security case tc4 passed
        self._populate_case_results(
            run_base.id,
            {
                self.tc1: ("failed", 100, [("accuracy", 0.0, False, {})]),
                self.tc2: ("failed", 100, [("accuracy", 0.0, False, {})]),
                self.tc3: ("failed", 100, [("accuracy", 0.0, False, {})]),
                self.tc4: ("passed", 100, [("security_policy", 1.0, True, {})]),
            },
        )

        # Candidate: tc1, tc2, tc3 fixed (+3), but security tc4 regresses to failed!
        self._populate_case_results(
            run_cand.id,
            {
                self.tc1: ("passed", 100, [("accuracy", 1.0, True, {})]),
                self.tc2: ("passed", 100, [("accuracy", 1.0, True, {})]),
                self.tc3: ("passed", 100, [("accuracy", 1.0, True, {})]),
                self.tc4: ("failed", 100, [("security_policy", 0.0, False, {})]),
            },
        )

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        # Security regression must cause verdict to be 'regressed' despite +50% net pass rate
        self.assertEqual(data["verdict"], "regressed")
        self.assertIn("security", data["verdict_explanation"].lower())
        self.assertEqual(len(data["regressions"]["security_regressions"]), 1)
        sec_reg = data["regressions"]["security_regressions"][0]
        self.assertEqual(sec_reg["test_case_id"], str(self.tc4.id))
        self.assertTrue(sec_reg["is_security"])

    def test_unchanged_performance(self):
        """Identical outcomes and scores produce 'unchanged' verdict."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        outcomes = {
            self.tc1: ("passed", 100, [("score_metric", 0.9, True, {})]),
            self.tc2: ("passed", 100, [("score_metric", 0.9, True, {})]),
            self.tc3: ("failed", 100, [("score_metric", 0.4, False, {})]),
            self.tc4: ("passed", 100, [("score_metric", 1.0, True, {})]),
        }
        self._populate_case_results(run_base.id, outcomes)
        self._populate_case_results(run_cand.id, outcomes)

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["verdict"], "unchanged")
        self.assertEqual(data["overall"]["pass_rate_delta"], 0.0)
        self.assertEqual(len(data["regressions"]["regressed_cases"]), 0)
        self.assertEqual(len(data["regressions"]["improved_cases"]), 0)
        self.assertEqual(data["regressions"]["both_passed_count"], 3)
        self.assertEqual(len(data["regressions"]["both_failed_cases"]), 1)

    def test_metric_score_differences_and_status(self):
        """Verifies calculation of individual metric averages, deltas, and improved/degraded categorization."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: accuracy=0.50, relevancy=0.90, safety=0.80
        self._populate_case_results(
            run_base.id,
            {
                self.tc1: ("passed", 100, [("accuracy", 0.50, True, {}), ("relevancy", 0.90, True, {})]),
                self.tc2: ("passed", 100, [("safety", 0.80, True, {})]),
            },
        )

        # Candidate: accuracy=0.85 (improved), relevancy=0.60 (degraded), safety=0.80 (unchanged)
        self._populate_case_results(
            run_cand.id,
            {
                self.tc1: ("passed", 100, [("accuracy", 0.85, True, {}), ("relevancy", 0.60, True, {})]),
                self.tc2: ("passed", 100, [("safety", 0.80, True, {})]),
            },
        )

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        metrics_data = {m["metric_name"]: m for m in data["metrics"]["metrics"]}

        # Accuracy
        self.assertEqual(metrics_data["accuracy"]["status"], "improved")
        self.assertAlmostEqual(metrics_data["accuracy"]["score_delta"], 0.35, places=3)
        self.assertIn("accuracy", data["metrics"]["improved_metrics"])

        # Relevancy
        self.assertEqual(metrics_data["relevancy"]["status"], "degraded")
        self.assertAlmostEqual(metrics_data["relevancy"]["score_delta"], -0.30, places=3)
        self.assertIn("relevancy", data["metrics"]["degraded_metrics"])

        # Safety
        self.assertEqual(metrics_data["safety"]["status"], "unchanged")
        self.assertAlmostEqual(metrics_data["safety"]["score_delta"], 0.0, places=3)
        self.assertIn("safety", data["metrics"]["unchanged_metrics"])

    def test_missing_or_non_applicable_metrics_not_treated_as_zero(self):
        """Non-applicable metrics are explicitly excluded and not defaulted to zero."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: faithfulness applicable on tc1 with 0.8, not applicable on tc2
        self._populate_case_results(
            run_base.id,
            {
                self.tc1: ("passed", 100, [("faithfulness", 0.80, True, {"applicable": True})]),
                self.tc2: ("passed", 100, [("faithfulness", 0.0, True, {"applicable": False})]),
            },
        )

        # Candidate: faithfulness was never evaluated in candidate
        self._populate_case_results(
            run_cand.id,
            {
                self.tc1: ("passed", 100, [("accuracy", 1.0, True, {})]),
                self.tc2: ("passed", 100, [("accuracy", 1.0, True, {})]),
            },
        )

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        metrics_data = {m["metric_name"]: m for m in data["metrics"]["metrics"]}
        faith_data = metrics_data["faithfulness"]

        # Baseline score should be 0.80 (excluding the non-applicable case), NOT (0.8 + 0.0)/2 = 0.40
        self.assertAlmostEqual(faith_data["baseline_score"], 0.80, places=2)
        # Candidate score must be None, NOT 0.0!
        self.assertIsNone(faith_data["candidate_score"])
        self.assertEqual(faith_data["status"], "only_in_baseline")

    def test_latency_comparison(self):
        """Verifies baseline/candidate latency calculation, delta, and percentage shift."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline latencies: 100, 150, 200, 150 -> mean = 150.0 ms
        self._populate_case_results(
            run_base.id,
            {
                self.tc1: ("passed", 100, []),
                self.tc2: ("passed", 150, []),
                self.tc3: ("passed", 200, []),
                self.tc4: ("passed", 150, []),
            },
        )

        # Candidate latencies: 60, 90, 120, 90 -> mean = 90.0 ms
        self._populate_case_results(
            run_cand.id,
            {
                self.tc1: ("passed", 60, []),
                self.tc2: ("passed", 90, []),
                self.tc3: ("passed", 120, []),
                self.tc4: ("passed", 90, []),
            },
        )

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand.id)},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()

        lat = data["latency"]
        self.assertEqual(lat["baseline_average_ms"], 150.0)
        self.assertEqual(lat["candidate_average_ms"], 90.0)
        self.assertEqual(lat["delta_ms"], -60.0)
        self.assertEqual(lat["percent_change"], -40.0)

    def test_missing_evaluation_run_returns_404(self):
        """Querying a non-existent run ID returns 404 Not Found."""
        run_base = self._create_run(self.assistant_v1.id)
        non_existent_id = uuid.uuid4()

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(non_existent_id)},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("not found", response.json()["detail"].lower())

    def test_incomplete_evaluation_run_returns_400(self):
        """Comparing runs that are in 'running' or 'pending' state returns 400 Bad Request."""
        run_base = self._create_run(self.assistant_v1.id, status="completed")
        run_cand_running = self._create_run(self.assistant_v2.id, status="running")

        response = self.client.post(
            "/api/evaluations/compare",
            json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_cand_running.id)},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not completed", response.json()["detail"].lower())

    def test_incompatible_projects_returns_400(self):
        """Comparing evaluation runs from different projects returns 400 Bad Request."""
        other_proj = Project(name="Other Project", slug=f"other-{uuid.uuid4().hex[:6]}")
        self.db.add(other_proj)
        self.db.commit()

        other_dataset = Dataset(project_id=other_proj.id, name="Other Dataset")
        other_av = AssistantVersion(
            project_id=other_proj.id,
            name="Other Assistant",
            version="1.0.0",
            provider="mock",
            model_name="mock",
        )
        self.db.add_all([other_dataset, other_av])
        self.db.commit()

        run_base = self._create_run(self.assistant_v1.id)
        run_other = self._create_run(
            other_av.id,
            project_id=other_proj.id,
            dataset_id=other_dataset.id,
        )

        try:
            response = self.client.post(
                "/api/evaluations/compare",
                json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_other.id)},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("different projects", response.json()["detail"].lower())
        finally:
            self.db.query(EvaluationRun).filter(EvaluationRun.id == run_other.id).delete(synchronize_session=False)
            self.db.query(AssistantVersion).filter(AssistantVersion.id == other_av.id).delete(synchronize_session=False)
            self.db.query(Dataset).filter(Dataset.id == other_dataset.id).delete(synchronize_session=False)
            self.db.query(Project).filter(Project.id == other_proj.id).delete(synchronize_session=False)
            self.db.commit()

    def test_incompatible_datasets_returns_400(self):
        """Comparing runs evaluated on different datasets returns 400 Bad Request."""
        second_dataset = Dataset(project_id=self.project.id, name="Second Dataset")
        self.db.add(second_dataset)
        self.db.commit()

        run_base = self._create_run(self.assistant_v1.id, dataset_id=self.dataset.id)
        run_diff_ds = self._create_run(self.assistant_v2.id, dataset_id=second_dataset.id)

        try:
            response = self.client.post(
                "/api/evaluations/compare",
                json={"baseline_run_id": str(run_base.id), "candidate_run_id": str(run_diff_ds.id)},
            )
            self.assertEqual(response.status_code, 400)
            self.assertIn("different datasets", response.json()["detail"].lower())
        finally:
            self.db.query(EvaluationRun).filter(EvaluationRun.id == run_diff_ds.id).delete(synchronize_session=False)
            self.db.query(Dataset).filter(Dataset.id == second_dataset.id).delete(synchronize_session=False)
            self.db.commit()


if __name__ == "__main__":
    unittest.main()
