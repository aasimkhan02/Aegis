"""Shared dependencies and helpers for FastAPI endpoints."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project import Project

DEFAULT_PROJECT_SLUG = "bharathome-ai"


def get_or_create_default_project(db: Session) -> Project:
    """Retrieve an existing project or create the default BharatHome AI workspace project."""
    project = db.scalar(
        select(Project).where(Project.slug == DEFAULT_PROJECT_SLUG)
    )
    if not project:
        # Fall back to any first project
        project = db.scalar(select(Project).order_by(Project.created_at))

    if not project:
        project = Project(
            name="BharatHome AI Support",
            slug=DEFAULT_PROJECT_SLUG,
            description="Evaluation workspace for BharatHome Appliances customer support assistants.",
        )
        db.add(project)
        db.commit()
        db.refresh(project)

    return project

