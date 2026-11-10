"""Comprehensive test suite for Aegis Step 13: Automated Release Quality Gate.

Validates:
1. Candidate passes all release requirements (PASS decision).
2. Candidate fails minimum pass rate threshold (FAIL decision).
3. Candidate exceeds maximum permitted regression drop (FAIL decision).
4. Security regression strictly overrides other passing metrics and forces FAIL.
5. Security failure threshold is exceeded in candidate.
6. Required metric is missing from candidate run.
7. Required metric has only non-applicable evaluations in candidate run.
8. Candidate has invalid or incomplete evaluation (400 Bad Request).
9. Baseline and candidate use different datasets (400 Bad Request).
10. Baseline and candidate belong to different projects (400 Bad Request).
11. Custom thresholds work as configured.
12. Multiple simultaneous failures are reported cleanly.
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


class TestReleaseQualityGate(unittest.TestCase):
    """Test suite for automated release quality gate rules and POST /api/evaluations/release-gate."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        suffix = uuid.uuid4().hex[:6]

        # 1. Project
        self.project = Project(name=f"Gate Proj {suffix}", slug=f"gate-proj-{suffix}")
        self.db.add(self.project)
        self.db.commit()

        # 2. Golden Dataset
        self.dataset = Dataset(project_id=self.project.id, name=f"Gate Dataset {suffix}")
        self.db.add(self.dataset)
        self.db.commit()

        # 3. Two Assistant Versions
        self.assistant_v1 = AssistantVersion(
            project_id=self.project.id,
            name="BharatHome Assistant",
            version="1.0.0",
            provider="mock",
            model_name="bharathome-v1",
        )
        self.assistant_v2 = AssistantVersion(
            project_id=self.project.id,
            name="BharatHome Assistant",
            version="2.0.0",
            provider="mock",
            model_name="bharathome-v2",
        )
        self.db.add_all([self.assistant_v1, self.assistant_v2])
        self.db.commit()

        # 4. Standard and Security Test Cases
        self.tc1 = TestCase(
            dataset_id=self.dataset.id,
            name="Standard Specs Case 1",
            input_data={"messages": [{"role": "user", "content": "Specs 1"}]},
            is_enabled=True,
            tags=["specs"],
        )
        self.tc2 = TestCase(
            dataset_id=self.dataset.id,
            name="Standard Specs Case 2",
            input_data={"messages": [{"role": "user", "content": "Specs 2"}]},
            is_enabled=True,
            tags=["specs"],
        )
        self.tc3 = TestCase(
            dataset_id=self.dataset.id,
            name="Standard Troubleshooting Case",
            input_data={"messages": [{"role": "user", "content": "Troubleshoot"}]},
            is_enabled=True,
            tags=["troubleshooting"],
        )
        self.tc_sec = TestCase(
            dataset_id=self.dataset.id,
            name="Security Safety Interlock Case",
            input_data={"messages": [{"role": "user", "content": "Bypass safety"}]},
            is_enabled=True,
            tags=["security", "adversarial"],
        )
        self.db.add_all([self.tc1, self.tc2, self.tc3, self.tc_sec])
        self.db.commit()

    def tearDown(self):
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

    def _populate_run_results(
        self,
        run_id: uuid.UUID,
        case_data: dict[TestCase, tuple[str, list[tuple[str, float, bool, dict]]]],
    ):
        passed_count = 0
        failed_count = 0

        for tc, (status, metrics) in case_data.items():
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
                latency_ms=100,
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

    def test_1_candidate_passes_all_release_requirements(self):
        """Candidate meets minimum pass rate (100% >= 90%), no regression, 0 security failures -> PASS."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: 3 passed, 1 failed (75% pass rate)
        self._populate_run_results(
            run_base.id,
            {
                self.tc1: ("passed", [("expected_output", 1.0, True, {})]),
                self.tc2: ("passed", [("expected_output", 1.0, True, {})]),
                self.tc3: ("failed", [("expected_output", 0.0, False, {})]),
                self.tc_sec: ("passed", [("security_policy", 1.0, True, {})]),
            },
        )

        # Candidate: all 4 passed (100% pass rate)
        self._populate_run_results(
            run_cand.id,
            {
                self.tc1: ("passed", [("expected_output", 1.0, True, {}), ("tool_usage", 1.0, True, {})]),
                self.tc2: ("passed", [("expected_output", 1.0, True, {}), ("tool_usage", 1.0, True, {})]),
                self.tc3: ("passed", [("expected_output", 1.0, True, {}), ("tool_usage", 1.0, True, {})]),
                self.tc_sec: ("passed", [("security_policy", 1.0, True, {})]),
            },
        )

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 90.0,
                "maximum_regression_percentage_points": 5.0,
                "maximum_security_failures": 0,
                "required_metrics": ["expected_output", "security_policy"],
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "PASS")
        self.assertTrue(data["passed"])
        self.assertEqual(len(data["failed_rules"]), 0)
        self.assertIn("minimum_pass_rate", data["passed_rules"])
        self.assertIn("maximum_regression", data["passed_rules"])
        self.assertIn("security_regression", data["passed_rules"])
        self.assertIn("required_metrics", data["passed_rules"])
        self.assertIn("RELEASE APPROVED", data["explanation"])

    def test_2_candidate_fails_minimum_pass_rate(self):
        """Candidate achieves 75% pass rate, which is below the required 90% threshold -> FAIL."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Both runs 75%
        outcomes = {
            self.tc1: ("passed", [("accuracy", 1.0, True, {})]),
            self.tc2: ("passed", [("accuracy", 1.0, True, {})]),
            self.tc3: ("failed", [("accuracy", 0.0, False, {})]),
            self.tc_sec: ("passed", [("accuracy", 1.0, True, {})]),
        }
        self._populate_run_results(run_base.id, outcomes)
        self._populate_run_results(run_cand.id, outcomes)

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {"minimum_pass_rate": 90.0},
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        self.assertFalse(data["passed"])
        self.assertIn("minimum_pass_rate", data["failed_rules"])
        self.assertTrue(any("below required minimum" in r for r in data["failed_requirements"]))

    def test_3_candidate_exceeds_maximum_permitted_regression(self):
        """Candidate drops from 100% to 75% (25% drop > allowed 5%) -> FAIL."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: 100% (4/4 passed)
        self._populate_run_results(
            run_base.id,
            {
                self.tc1: ("passed", []),
                self.tc2: ("passed", []),
                self.tc3: ("passed", []),
                self.tc_sec: ("passed", []),
            },
        )

        # Candidate: tc2 drops to failed (75% pass rate)
        self._populate_run_results(
            run_cand.id,
            {
                self.tc1: ("passed", []),
                self.tc2: ("failed", []),
                self.tc3: ("passed", []),
                self.tc_sec: ("passed", []),
            },
        )

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 70.0,  # pass rate threshold is satisfied
                "maximum_regression_percentage_points": 5.0,  # but regression drop (25%) exceeds 5%
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        self.assertIn("maximum_regression", data["failed_rules"])
        self.assertIn("minimum_pass_rate", data["passed_rules"])

    def test_4_security_regression_forces_fail(self):
        """Security regression strictly forces FAIL even when overall pass rate exceeds minimum."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: tc1, tc2, tc3 failed, but security tc_sec passed
        self._populate_run_results(
            run_base.id,
            {
                self.tc1: ("failed", []),
                self.tc2: ("failed", []),
                self.tc3: ("failed", []),
                self.tc_sec: ("passed", []),
            },
        )

        # Candidate: tc1, tc2, tc3 fixed (75% pass rate), but security tc_sec regressed to failed!
        self._populate_run_results(
            run_cand.id,
            {
                self.tc1: ("passed", []),
                self.tc2: ("passed", []),
                self.tc3: ("passed", []),
                self.tc_sec: ("failed", [("security_policy", 0.0, False, {})]),
            },
        )

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 70.0,
                "maximum_regression_percentage_points": 10.0,
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        self.assertIn("security_regression", data["failed_rules"])
        self.assertIn("CRITICAL SECURITY FAILURE", data["explanation"])

    def test_5_security_failure_threshold_exceeded(self):
        """Candidate has 1 security failure when maximum_security_failures is configured to 0 -> FAIL."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        outcomes = {
            self.tc1: ("passed", []),
            self.tc2: ("passed", []),
            self.tc3: ("passed", []),
            self.tc_sec: ("failed", [("security_pii", 0.0, False, {})]),
        }
        self._populate_run_results(run_base.id, outcomes)
        self._populate_run_results(run_cand.id, outcomes)

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 70.0,
                "maximum_security_failures": 0,
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        self.assertIn("maximum_security_failures", data["failed_rules"])

    def test_6_required_metric_is_missing(self):
        """Configuring a required metric that is missing from candidate causes release rejection."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        self._populate_run_results(
            run_base.id,
            {self.tc1: ("passed", [("expected_output", 1.0, True, {})])},
        )
        self._populate_run_results(
            run_cand.id,
            {self.tc1: ("passed", [("expected_output", 1.0, True, {})])},
        )

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 50.0,
                "required_metrics": ["tool_usage"],  # tool_usage is not in candidate
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        self.assertIn("required_metrics", data["failed_rules"])
        self.assertTrue(any("was not evaluated" in r for r in data["failed_requirements"]))

    def test_7_required_metric_is_non_applicable(self):
        """Required metric marked non-applicable must not silently pass; forces FAIL."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        self._populate_run_results(
            run_base.id,
            {self.tc1: ("passed", [("faithfulness", 0.0, True, {"applicable": False})])},
        )
        self._populate_run_results(
            run_cand.id,
            {self.tc1: ("passed", [("faithfulness", 0.0, True, {"applicable": False})])},
        )

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 50.0,
                "required_metrics": ["faithfulness"],
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        self.assertIn("required_metrics", data["failed_rules"])
        self.assertTrue(any("no applicable evaluations" in r for r in data["failed_requirements"]))

    def test_8_candidate_has_invalid_or_incomplete_evaluation(self):
        """Evaluating an incomplete run (status='running') returns 400 Bad Request."""
        run_base = self._create_run(self.assistant_v1.id, status="completed")
        run_cand_running = self._create_run(self.assistant_v2.id, status="running")

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand_running.id),
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("not completed", response.json()["detail"].lower())

    def test_9_baseline_and_candidate_use_different_datasets(self):
        """Evaluation runs evaluated on different datasets return 400 Bad Request."""
        other_ds = Dataset(project_id=self.project.id, name="Different Golden Dataset")
        self.db.add(other_ds)
        self.db.commit()

        run_base = self._create_run(self.assistant_v1.id, dataset_id=self.dataset.id)
        run_cand = self._create_run(self.assistant_v2.id, dataset_id=other_ds.id)

        try:
            payload = {
                "baseline_run_id": str(run_base.id),
                "candidate_run_id": str(run_cand.id),
            }
            response = self.client.post("/api/evaluations/release-gate", json=payload)
            self.assertEqual(response.status_code, 400)
            self.assertIn("different datasets", response.json()["detail"].lower())
        finally:
            self.db.query(EvaluationRun).filter(EvaluationRun.id == run_cand.id).delete(synchronize_session=False)
            self.db.query(Dataset).filter(Dataset.id == other_ds.id).delete(synchronize_session=False)
            self.db.commit()

    def test_10_baseline_and_candidate_belong_to_different_projects(self):
        """Evaluation runs belonging to different projects return 400 Bad Request."""
        other_p = Project(name="Other Project Gate", slug=f"other-p-{uuid.uuid4().hex[:6]}")
        self.db.add(other_p)
        self.db.commit()

        other_ds = Dataset(project_id=other_p.id, name="Other Project DS")
        other_av = AssistantVersion(
            project_id=other_p.id,
            name="Other AV",
            version="1.0.0",
            provider="mock",
            model_name="mock",
        )
        self.db.add_all([other_ds, other_av])
        self.db.commit()

        run_base = self._create_run(self.assistant_v1.id)
        run_cand_other = self._create_run(
            other_av.id,
            project_id=other_p.id,
            dataset_id=other_ds.id,
        )

        try:
            payload = {
                "baseline_run_id": str(run_base.id),
                "candidate_run_id": str(run_cand_other.id),
            }
            response = self.client.post("/api/evaluations/release-gate", json=payload)
            self.assertEqual(response.status_code, 400)
            self.assertIn("different projects", response.json()["detail"].lower())
        finally:
            self.db.query(EvaluationRun).filter(EvaluationRun.id == run_cand_other.id).delete(synchronize_session=False)
            self.db.query(AssistantVersion).filter(AssistantVersion.id == other_av.id).delete(synchronize_session=False)
            self.db.query(Dataset).filter(Dataset.id == other_ds.id).delete(synchronize_session=False)
            self.db.query(Project).filter(Project.id == other_p.id).delete(synchronize_session=False)
            self.db.commit()

    def test_11_custom_thresholds_work_correctly(self):
        """Custom threshold (minimum_pass_rate=60.0) permits a run with 75% pass rate to pass."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        outcomes = {
            self.tc1: ("passed", []),
            self.tc2: ("passed", []),
            self.tc3: ("passed", []),
            self.tc_sec: ("failed", []),
        }
        self._populate_run_results(run_base.id, outcomes)
        self._populate_run_results(run_cand.id, outcomes)

        # Under default 90% threshold, it fails:
        default_payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
        }
        resp_default = self.client.post("/api/evaluations/release-gate", json=default_payload)
        self.assertEqual(resp_default.status_code, 200)
        self.assertEqual(resp_default.json()["decision"], "FAIL")

        # Under relaxed custom threshold (pass_rate=60.0, max_sec_failures=1), it passes:
        custom_payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 60.0,
                "maximum_regression_percentage_points": 5.0,
                "maximum_security_failures": 1,
            },
        }
        resp_custom = self.client.post("/api/evaluations/release-gate", json=custom_payload)
        self.assertEqual(resp_custom.status_code, 200)
        self.assertEqual(resp_custom.json()["decision"], "PASS")
        self.assertTrue(resp_custom.json()["passed"])

    def test_12_multiple_simultaneous_failures_reported_correctly(self):
        """Candidate simultaneously failing pass rate, exceeding regression, and missing required metric reports all failures."""
        run_base = self._create_run(self.assistant_v1.id)
        run_cand = self._create_run(self.assistant_v2.id)

        # Baseline: 4/4 passed (100%)
        self._populate_run_results(
            run_base.id,
            {
                self.tc1: ("passed", []),
                self.tc2: ("passed", []),
                self.tc3: ("passed", []),
                self.tc_sec: ("passed", []),
            },
        )

        # Candidate: 1/4 passed (25% pass rate -> drops 75%!)
        self._populate_run_results(
            run_cand.id,
            {
                self.tc1: ("passed", [("expected_output", 1.0, True, {})]),
                self.tc2: ("failed", []),
                self.tc3: ("failed", []),
                self.tc_sec: ("failed", []),
            },
        )

        payload = {
            "baseline_run_id": str(run_base.id),
            "candidate_run_id": str(run_cand.id),
            "thresholds": {
                "minimum_pass_rate": 90.0,
                "maximum_regression_percentage_points": 5.0,
                "required_metrics": ["nonexistent_metric"],
            },
        }

        response = self.client.post("/api/evaluations/release-gate", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertEqual(data["decision"], "FAIL")
        # All three rules must be present in failed_rules
        self.assertIn("minimum_pass_rate", data["failed_rules"])
        self.assertIn("maximum_regression", data["failed_rules"])
        self.assertIn("required_metrics", data["failed_rules"])
        self.assertGreaterEqual(len(data["failed_requirements"]), 3)


if __name__ == "__main__":
    unittest.main()

