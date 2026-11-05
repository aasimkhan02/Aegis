"""Seed script to load the BharatHome Golden Dataset into PostgreSQL."""

import json
from pathlib import Path
import sys

# Ensure backend root is on sys.path
backend_root = Path(__file__).resolve().parent.parent
if str(backend_root) not in sys.path:
    sys.path.insert(0, str(backend_root))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_or_create_default_project
from app.db.session import SessionLocal
from app.models.dataset import Dataset
from app.models.test_case import TestCase


def seed_golden_dataset() -> None:
    fixture_path = backend_root / "data" / "bharathome_golden_dataset.json"
    if not fixture_path.exists():
        print(f"[FAIL] Fixture file not found: {fixture_path}")
        sys.exit(1)

    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    db: Session = SessionLocal()
    try:
        project = get_or_create_default_project(db)
        dataset_name = data.get("name", "BharatHome Customer Support Golden Dataset")

        # Check if dataset already exists
        dataset = db.scalar(
            select(Dataset).where(
                Dataset.project_id == project.id,
                Dataset.name == dataset_name,
            )
        )

        if not dataset:
            dataset = Dataset(
                project_id=project.id,
                name=dataset_name,
                description=data.get("description", ""),
                metadata=data.get("metadata", {}),
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            print(f"[+] Created Dataset: {dataset.name} (id: {dataset.id})")
        else:
            print(f"[*] Found existing Dataset: {dataset.name} (id: {dataset.id})")

        # Check existing test cases
        existing_cases = {
            tc.name: tc for tc in db.scalars(select(TestCase).where(TestCase.dataset_id == dataset.id)).all()
        }

        added = 0
        updated = 0
        for item in data.get("test_cases", []):
            name = item["name"]
            if name in existing_cases:
                tc = existing_cases[name]
                tc.input_data = item.get("input_data", {})
                tc.expected_output = item.get("expected_output")
                tc.expected_behavior = item.get("expected_behavior")
                tc.retrieval_context = item.get("retrieval_context", [])
                tc.tags = item.get("tags", [])
                tc.metadata_ = item.get("metadata", {})
                tc.is_enabled = item.get("is_enabled", True)
                updated += 1
            else:
                tc = TestCase(
                    dataset_id=dataset.id,
                    name=name,
                    input_data=item.get("input_data", {}),
                    expected_output=item.get("expected_output"),
                    expected_behavior=item.get("expected_behavior"),
                    retrieval_context=item.get("retrieval_context", []),
                    tags=item.get("tags", []),
                    metadata=item.get("metadata", {}),
                    is_enabled=item.get("is_enabled", True),
                )
                db.add(tc)
                added += 1

        db.commit()
        print(f"[SUCCESS] Golden Dataset seeded successfully! Added: {added}, Updated: {updated}, Total: {len(data['test_cases'])}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_golden_dataset()

