"""Tests for Aegis Step 14: Dashboard Analytics, Project Management, and Assistant API endpoints."""

import unittest
import uuid
from fastapi.testclient import TestClient

from app.db.session import SessionLocal
from app.main import app
from app.models.assistant_version import AssistantVersion
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.project import Project


class TestDashboardAndManagementAPI(unittest.TestCase):
    """Test dashboard metrics, projects, and assistants API endpoints."""

    def setUp(self):
        self.client = TestClient(app)
        self.db = SessionLocal()
        suffix = uuid.uuid4().hex[:6]

        self.project = Project(
            name=f"Dashboard Test Proj {suffix}",
            slug=f"dash-proj-{suffix}",
            description="Project created for dashboard tests",
        )
        self.db.add(self.project)
        self.db.commit()

        self.assistant = AssistantVersion(
            project_id=self.project.id,
            name="Dashboard Assistant",
            version="1.0.0",
            provider="mock",
            model_name="mock-model",
        )
        self.dataset = Dataset(
            project_id=self.project.id,
            name=f"Dashboard Dataset {suffix}",
        )
        self.db.add_all([self.assistant, self.dataset])
        self.db.commit()

    def tearDown(self):
        self.db.query(EvaluationRun).filter(EvaluationRun.project_id == self.project.id).delete(synchronize_session=False)
        self.db.query(Dataset).filter(Dataset.id == self.dataset.id).delete(synchronize_session=False)
        self.db.query(AssistantVersion).filter(AssistantVersion.project_id == self.project.id).delete(synchronize_session=False)
        self.db.query(Project).filter(Project.id == self.project.id).delete(synchronize_session=False)
        self.db.commit()
        self.db.close()

    def test_get_dashboard_stats(self):
        """GET /api/dashboard/stats returns real aggregated metrics."""
        response = self.client.get("/api/dashboard/stats")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("total_projects", data)
        self.assertIn("total_assistants", data)
        self.assertIn("total_datasets", data)
        self.assertIn("total_evaluation_runs", data)
        self.assertIn("overall_pass_rate", data)
        self.assertGreaterEqual(data["total_projects"], 1)

    def test_get_dashboard_security(self):
        """GET /api/dashboard/security returns security breakdown and findings."""
        response = self.client.get("/api/dashboard/security")
        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertIn("total_security_cases", data)
        self.assertIn("security_pass_rate", data)
        self.assertIn("validator_breakdown", data)
        self.assertIn("findings", data)

    def test_list_and_create_projects(self):
        """POST /api/projects creates a project; GET /api/projects lists projects with counts."""
        new_suffix = uuid.uuid4().hex[:6]
        payload = {
            "name": f"New Test Project {new_suffix}",
            "description": "Testing project creation",
        }
        res_create = self.client.post("/api/projects", json=payload)
        self.assertEqual(res_create.status_code, 201)
        created = res_create.json()
        self.assertEqual(created["name"], payload["name"])
        self.assertTrue(len(created["slug"]) > 0)
        proj_id = created["id"]

        try:
            res_list = self.client.get(f"/api/projects?search={new_suffix}")
            self.assertEqual(res_list.status_code, 200)
            items = res_list.json()["items"]
            self.assertEqual(len(items), 1)
            self.assertEqual(items[0]["id"], proj_id)

            res_get = self.client.get(f"/api/projects/{proj_id}")
            self.assertEqual(res_get.status_code, 200)
            self.assertEqual(res_get.json()["name"], payload["name"])
        finally:
            self.db.query(Project).filter(Project.id == proj_id).delete(synchronize_session=False)
            self.db.commit()

    def test_list_and_create_assistants(self):
        """POST /api/assistants registers a version; GET /api/assistants lists versions."""
        payload = {
            "project_id": str(self.project.id),
            "name": "Custom Support Bot",
            "version": "2.5.0",
            "provider": "mock",
            "model_name": "custom-v2",
        }
        res_create = self.client.post("/api/assistants", json=payload)
        self.assertEqual(res_create.status_code, 201)
        created = res_create.json()
        self.assertEqual(created["version"], "2.5.0")
        asst_id = created["id"]

        try:
            res_list = self.client.get(f"/api/assistants?project_id={self.project.id}")
            self.assertEqual(res_list.status_code, 200)
            items = res_list.json()["items"]
            self.assertTrue(any(a["id"] == asst_id for a in items))
        finally:
            self.db.query(AssistantVersion).filter(AssistantVersion.id == asst_id).delete(synchronize_session=False)
            self.db.commit()

    def test_evaluations_enriched_fields(self):
        """GET /api/evaluations returns enriched fields (names, versions, pass rates)."""
        run = EvaluationRun(
            project_id=self.project.id,
            assistant_version_id=self.assistant.id,
            dataset_id=self.dataset.id,
            status="completed",
            total_cases=10,
            passed_cases=8,
            failed_cases=2,
        )
        self.db.add(run)
        self.db.commit()

        try:
            res = self.client.get(f"/api/evaluations?project_id={self.project.id}")
            self.assertEqual(res.status_code, 200)
            items = res.json()["items"]
            self.assertEqual(len(items), 1)
            item = items[0]
            self.assertEqual(item["project_name"], self.project.name)
            self.assertEqual(item["assistant_name"], self.assistant.name)
            self.assertEqual(item["assistant_version_tag"], self.assistant.version)
            self.assertEqual(item["dataset_name"], self.dataset.name)
            self.assertEqual(item["pass_rate"], 80.0)
        finally:
            self.db.query(EvaluationRun).filter(EvaluationRun.id == run.id).delete(synchronize_session=False)
            self.db.commit()


if __name__ == "__main__":
    unittest.main()
