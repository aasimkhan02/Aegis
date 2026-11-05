"""Seed script to persist BharatHome Assistant v1 and v2 in the database."""

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
from app.demo.assistants import (
    BHARATHOME_V1_CONFIG,
    BHARATHOME_V1_MODEL,
    BHARATHOME_V1_NAME,
    BHARATHOME_V1_PROVIDER,
    BHARATHOME_V1_SYSTEM_PROMPT,
    BHARATHOME_V1_VERSION,
    BHARATHOME_V2_CONFIG,
    BHARATHOME_V2_MODEL,
    BHARATHOME_V2_NAME,
    BHARATHOME_V2_PROVIDER,
    BHARATHOME_V2_SYSTEM_PROMPT,
    BHARATHOME_V2_VERSION,
)
from app.models.assistant_version import AssistantVersion


def seed_assistant_versions() -> tuple[AssistantVersion, AssistantVersion]:
    """Persist both v1 (good) and v2 (broken) assistant versions in PostgreSQL."""
    db: Session = SessionLocal()
    try:
        project = get_or_create_default_project(db)
        print(f"[INFO] Using project: '{project.name}' (id: {project.id}, slug: {project.slug})")

        # 1. BharatHome Assistant v1 (Good)
        v1 = db.scalar(
            select(AssistantVersion).where(
                AssistantVersion.project_id == project.id,
                AssistantVersion.version == BHARATHOME_V1_VERSION,
            )
        )
        if not v1:
            v1 = AssistantVersion(
                project_id=project.id,
                name=BHARATHOME_V1_NAME,
                version=BHARATHOME_V1_VERSION,
                provider=BHARATHOME_V1_PROVIDER,
                model_name=BHARATHOME_V1_MODEL,
                system_prompt=BHARATHOME_V1_SYSTEM_PROMPT,
                config=BHARATHOME_V1_CONFIG,
            )
            db.add(v1)
            print(f"[OK] Added assistant version: {BHARATHOME_V1_NAME} ({BHARATHOME_V1_VERSION})")
        else:
            v1.name = BHARATHOME_V1_NAME
            v1.provider = BHARATHOME_V1_PROVIDER
            v1.model_name = BHARATHOME_V1_MODEL
            v1.system_prompt = BHARATHOME_V1_SYSTEM_PROMPT
            v1.config = BHARATHOME_V1_CONFIG
            print(f"[OK] Updated assistant version: {BHARATHOME_V1_NAME} ({BHARATHOME_V1_VERSION})")

        # 2. BharatHome Assistant v2 (Broken)
        v2 = db.scalar(
            select(AssistantVersion).where(
                AssistantVersion.project_id == project.id,
                AssistantVersion.version == BHARATHOME_V2_VERSION,
            )
        )
        if not v2:
            v2 = AssistantVersion(
                project_id=project.id,
                name=BHARATHOME_V2_NAME,
                version=BHARATHOME_V2_VERSION,
                provider=BHARATHOME_V2_PROVIDER,
                model_name=BHARATHOME_V2_MODEL,
                system_prompt=BHARATHOME_V2_SYSTEM_PROMPT,
                config=BHARATHOME_V2_CONFIG,
            )
            db.add(v2)
            print(f"[OK] Added assistant version: {BHARATHOME_V2_NAME} ({BHARATHOME_V2_VERSION})")
        else:
            v2.name = BHARATHOME_V2_NAME
            v2.provider = BHARATHOME_V2_PROVIDER
            v2.model_name = BHARATHOME_V2_MODEL
            v2.system_prompt = BHARATHOME_V2_SYSTEM_PROMPT
            v2.config = BHARATHOME_V2_CONFIG
            print(f"[OK] Updated assistant version: {BHARATHOME_V2_NAME} ({BHARATHOME_V2_VERSION})")

        db.commit()
        db.refresh(v1)
        db.refresh(v2)
        print(f"[SUCCESS] Persisted assistant versions in PostgreSQL:")
        print(f"  - v1 ID: {v1.id} | Name: {v1.name} | Model: {v1.model_name}")
        print(f"  - v2 ID: {v2.id} | Name: {v2.name} | Model: {v2.model_name}")
        return v1, v2
    except Exception as e:
        db.rollback()
        print(f"[FAIL] Error seeding assistant versions: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_assistant_versions()

