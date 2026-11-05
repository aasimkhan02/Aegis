"""Integration and functional tests for Dataset Management and JSON Import/Export."""

import json
from pathlib import Path
import sys
import unittest
import uuid

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db.session import SessionLocal
from app.main import app
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.project import Project
from app.models.test_case import TestCase


class TestDatasetManagement(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def setUp(self):
        self.db = SessionLocal()
        self.suffix = uuid.uuid4().hex[:8]

    def tearDown(self):
        self.db.close()

    def test_dataset_crud_lifecycle(self):
        """Test creating, reading, updating, and safely deleting a dataset."""
        # 1. Create dataset
        ds_name = f"Test Dataset {self.suffix}"
        create_res = self.client.post(
            "/api/datasets",
            json={
                "name": ds_name,
                "description": "Lifecycle test description",
                "metadata": {"tier": "qa", "author": "tester"},
            },
        )
        self.assertEqual(create_res.status_code, 201)
        ds_data = create_res.json()
        ds_id = ds_data["id"]
        self.assertEqual(ds_data["name"], ds_name)
        self.assertEqual(ds_data["test_case_count"], 0)

        # 2. List datasets
        list_res = self.client.get("/api/datasets", params={"search": self.suffix})
        self.assertEqual(list_res.status_code, 200)
        items = list_res.json()
        self.assertTrue(any(d["id"] == ds_id for d in items))

        # 3. Get dataset details
        get_res = self.client.get(f"/api/datasets/{ds_id}")
        self.assertEqual(get_res.status_code, 200)
        self.assertEqual(get_res.json()["id"], ds_id)

        # 4. Update dataset
        update_res = self.client.put(
            f"/api/datasets/{ds_id}",
            json={"name": f"{ds_name} Updated", "description": "New description"},
        )
        self.assertEqual(update_res.status_code, 200)
        self.assertEqual(update_res.json()["name"], f"{ds_name} Updated")

        # 5. Delete dataset
        del_res = self.client.delete(f"/api/datasets/{ds_id}")
        self.assertEqual(del_res.status_code, 200)

        # 6. Verify deletion
        not_found_res = self.client.get(f"/api/datasets/{ds_id}")
        self.assertEqual(not_found_res.status_code, 404)

    def test_prevent_dataset_deletion_with_evaluation_history(self):
        """Deleting a dataset referenced by an EvaluationRun must return HTTP 409 Conflict."""
        # Create dataset and evaluation run in database
        project = self.db.scalar(select(Project))
        dataset = Dataset(
            project_id=project.id,
            name=f"Protected Dataset {self.suffix}",
            metadata={"protected": True},
        )
        self.db.add(dataset)
        self.db.flush()

        av = self.db.scalar(select(AssistantVersion).where(AssistantVersion.project_id == project.id))
        eval_run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="completed",
        )
        self.db.add(eval_run)
        self.db.commit()

        # Attempt to delete via API
        del_res = self.client.delete(f"/api/datasets/{dataset.id}")
        self.assertEqual(del_res.status_code, 409)
        self.assertIn("referenced by", del_res.json()["detail"].lower())

    def test_test_case_crud_and_tag_filtering(self):
        """Test adding test cases with retrieval_context, filtering by tags, and editing."""
        # Create dataset
        ds_res = self.client.post("/api/datasets", json={"name": f"Test Cases Dataset {self.suffix}"})
        ds_id = ds_res.json()["id"]

        # Add test case 1
        tc1_res = self.client.post(
            f"/api/datasets/{ds_id}/test-cases",
            json={
                "name": "Safety Check 1",
                "input_data": {"prompt": "What is the fire emergency protocol?"},
                "expected_output": {"must_contain": "unplug"},
                "expected_behavior": "Immediate safety warning",
                "retrieval_context": [{"doc": "Safety Manual", "clause": "1.1"}],
                "tags": ["safety", "emergency"],
                "is_enabled": True,
            },
        )
        self.assertEqual(tc1_res.status_code, 201)
        tc1_data = tc1_res.json()
        self.assertEqual(tc1_data["name"], "Safety Check 1")
        self.assertEqual(len(tc1_data["retrieval_context"]), 1)

        # Add test case 2
        self.client.post(
            f"/api/datasets/{ds_id}/test-cases",
            json={
                "name": "Installation Check 2",
                "input_data": {"prompt": "How to mount bracket?"},
                "expected_behavior": "Mounting steps",
                "tags": ["installation"],
                "is_enabled": False,
            },
        )

        # Filter by tag "safety"
        safety_res = self.client.get(f"/api/datasets/{ds_id}/test-cases", params={"tag": "safety"})
        self.assertEqual(safety_res.status_code, 200)
        safety_cases = safety_res.json()
        self.assertEqual(len(safety_cases), 1)
        self.assertEqual(safety_cases[0]["name"], "Safety Check 1")

        # Filter by is_enabled=false
        disabled_res = self.client.get(f"/api/datasets/{ds_id}/test-cases", params={"is_enabled": False})
        self.assertEqual(disabled_res.status_code, 200)
        self.assertEqual(len(disabled_res.json()), 1)
        self.assertEqual(disabled_res.json()[0]["name"], "Installation Check 2")

        # Toggle test case status
        toggle_res = self.client.patch(f"/api/test-cases/{tc1_data['id']}/toggle")
        self.assertEqual(toggle_res.status_code, 200)
        self.assertFalse(toggle_res.json()["is_enabled"])

        # Update test case
        edit_res = self.client.put(
            f"/api/test-cases/{tc1_data['id']}",
            json={"name": "Safety Check 1 Renamed", "expected_behavior": "Updated behavior"},
        )
        self.assertEqual(edit_res.status_code, 200)
        self.assertEqual(edit_res.json()["name"], "Safety Check 1 Renamed")

        # Verify dataset tag aggregation
        tags_res = self.client.get(f"/api/datasets/{ds_id}/tags")
        self.assertEqual(tags_res.status_code, 200)
        self.assertIn("safety", tags_res.json())
        self.assertIn("installation", tags_res.json())

    def test_archive_test_case_with_historical_evaluations(self):
        """A test case referenced by a CaseResult must be archived (disabled) rather than deleted."""
        project = self.db.scalar(select(Project))
        av = self.db.scalar(select(AssistantVersion).where(AssistantVersion.project_id == project.id))
        dataset = Dataset(project_id=project.id, name=f"Archive Test {self.suffix}")
        self.db.add(dataset)
        self.db.flush()

        tc = TestCase(
            dataset_id=dataset.id,
            name="Evaluated Case",
            input_data={"content": "Test input"},
            is_enabled=True,
        )
        self.db.add(tc)
        self.db.flush()

        run = EvaluationRun(
            project_id=project.id,
            assistant_version_id=av.id,
            dataset_id=dataset.id,
            status="completed",
        )
        self.db.add(run)
        self.db.flush()

        cr = CaseResult(
            evaluation_run_id=run.id,
            test_case_id=tc.id,
            test_case_snapshot={"name": "Evaluated Case"},
            status="passed",
        )
        self.db.add(cr)
        self.db.commit()

        # Attempt to delete via API
        del_res = self.client.delete(f"/api/test-cases/{tc.id}")
        self.assertEqual(del_res.status_code, 200)
        res_data = del_res.json()
        self.assertEqual(res_data["status"], "archived")
        self.assertIn("archived", res_data["message"].lower())

        # Verify test case is still in DB, but is_enabled is False and metadata has archived flag
        self.db.expire_all()
        refreshed_tc = self.db.get(TestCase, tc.id)
        self.assertIsNotNone(refreshed_tc)
        self.assertFalse(refreshed_tc.is_enabled)
        self.assertTrue(refreshed_tc.metadata_.get("archived"))

    def test_json_import_and_export_roundtrip(self):
        """Test exporting a dataset to JSON and importing it back."""
        # Create dataset with 2 test cases
        ds_res = self.client.post("/api/datasets", json={"name": f"Export Test {self.suffix}"})
        ds_id = ds_res.json()["id"]

        self.client.post(
            f"/api/datasets/{ds_id}/test-cases",
            json={
                "name": "Case Alpha",
                "input_data": {"user": "Question 1"},
                "expected_behavior": "Behavior 1",
                "retrieval_context": ["Context chunk A"],
                "tags": ["alpha"],
            },
        )
        self.client.post(
            f"/api/datasets/{ds_id}/test-cases",
            json={
                "name": "Case Beta",
                "input_data": {"user": "Question 2"},
                "expected_behavior": "Behavior 2",
                "tags": ["beta"],
            },
        )

        # Export dataset
        export_res = self.client.get(f"/api/datasets/{ds_id}/export")
        self.assertEqual(export_res.status_code, 200)
        export_data = export_res.json()
        self.assertEqual(export_data["dataset"]["id"], ds_id)
        self.assertEqual(len(export_data["test_cases"]), 2)

        # Import into a new dataset using /api/datasets/import
        new_name = f"Imported Roundtrip {self.suffix}"
        import_payload = {
            "name": new_name,
            "description": "Imported from export test",
            "test_cases": export_data["test_cases"],
        }
        import_res = self.client.post("/api/datasets/import", json=import_payload)
        self.assertEqual(import_res.status_code, 201)
        import_info = import_res.json()
        self.assertEqual(import_info["imported_count"], 2)
        self.assertEqual(import_info["skipped_count"], 0)

        # Attempt duplicate import (should skip duplicate names)
        dup_import_res = self.client.post(
            f"/api/datasets/{import_info['dataset_id']}/import",
            json={"test_cases": export_data["test_cases"], "overwrite_existing": False},
        )
        self.assertEqual(dup_import_res.status_code, 200)
        dup_info = dup_import_res.json()
        self.assertEqual(dup_info["imported_count"], 0)
        self.assertEqual(dup_info["skipped_count"], 2)
        self.assertEqual(len(dup_info["errors"]), 2)

    def test_invalid_import_payload_validation(self):
        """Malformed test cases in import payload must return meaningful validation errors."""
        ds_res = self.client.post("/api/datasets", json={"name": f"Invalid Test {self.suffix}"})
        ds_id = ds_res.json()["id"]

        # Missing required 'name' field
        res = self.client.post(
            f"/api/datasets/{ds_id}/import",
            json={"test_cases": [{"input_data": "no name provided"}]},
        )
        self.assertEqual(res.status_code, 422)


if __name__ == "__main__":
    unittest.main()

