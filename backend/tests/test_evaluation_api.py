"""API integration tests for evaluation endpoints."""

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


class TestEvaluationAPI(unittest.TestCase):
    """Test the FastAPI evaluation endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        suffix = uuid.uuid4().hex[:6]

        self.project = Project(name=f"API Test Proj {suffix}", slug=f"api-proj-{suffix}")
        self.db.add(self.project)
        self.db.commit()

        self.dataset = Dataset(project_id=self.project.id, name=f"API Dataset {suffix}")
        self.assistant = AssistantVersion(
            project_id=self.project.id,
            name="API Assistant",
            version="1.0.0",
            provider="mock",
            model_name="mock-model",
        )
        self.db.add_all([self.dataset, self.assistant])
        self.db.commit()

        self.tc1 = TestCase(
            dataset_id=self.dataset.id,
            name="API Case 1",
            input_data={"messages": [{"role": "user", "content": "Hello"}]},
            expected_output={"exact": "Hello"},
            is_enabled=True,
        )
        self.db.add(self.tc1)
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
        self.db.query(AssistantVersion).filter(AssistantVersion.id == self.assistant.id).delete(synchronize_session=False)
        self.db.query(Project).filter(Project.id == self.project.id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_start_evaluation_success(self):
        payload = {
            "assistant_version_id": str(self.assistant.id),
            "dataset_id": str(self.dataset.id),
            "config": {"max_concurrency": 1, "fail_fast": False},
        }
        response = self.client.post("/api/evaluations", json=payload)
        self.assertEqual(response.status_code, 202)
        data = response.json()
        self.assertEqual(data["status"], "pending")
        self.assertEqual(data["total_cases"], 1)
        self.assertEqual(data["project_id"], str(self.project.id))

    def test_start_evaluation_incompatible_project_409(self):
        other_proj = Project(name="Other P", slug=f"other-{uuid.uuid4().hex[:6]}")
        self.db.add(other_proj)
        self.db.commit()
        try:
            other_av = AssistantVersion(
                project_id=other_proj.id,
                name="Other AV",
                version="1.0.0",
                provider="mock",
                model_name="mock-model",
            )
            self.db.add(other_av)
            self.db.commit()

            payload = {
                "assistant_version_id": str(other_av.id),
                "dataset_id": str(self.dataset.id),
            }
            response = self.client.post("/api/evaluations", json=payload)
            self.assertEqual(response.status_code, 409)
            self.assertIn("Incompatible project", response.json()["detail"])
        finally:
            self.db.query(AssistantVersion).filter(AssistantVersion.project_id == other_proj.id).delete()
            self.db.query(Project).filter(Project.id == other_proj.id).delete()
            self.db.commit()

    def test_start_evaluation_nonexistent_assistant_404(self):
        payload = {
            "assistant_version_id": str(uuid.uuid4()),
            "dataset_id": str(self.dataset.id),
        }
        response = self.client.post("/api/evaluations", json=payload)
        self.assertEqual(response.status_code, 404)

    def test_list_evaluations(self):
        response = self.client.get(f"/api/evaluations?project_id={self.project.id}")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("items", data)
        self.assertIn("total", data)

    def test_get_evaluation_not_found_404(self):
        random_id = str(uuid.uuid4())
        response = self.client.get(f"/api/evaluations/{random_id}")
        self.assertEqual(response.status_code, 404)

    def test_get_case_results_not_found_404(self):
        random_id = str(uuid.uuid4())
        response = self.client.get(f"/api/evaluations/{random_id}/results")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()

