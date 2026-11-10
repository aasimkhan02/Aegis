"""FastAPI endpoints for Project management."""

import re
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.assistant_version import AssistantVersion
from app.models.dataset import Dataset
from app.models.evaluation_run import EvaluationRun
from app.models.project import Project
from app.schemas.project import (
    ProjectCreate,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
)

router = APIRouter()


def _slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", text.lower()).strip()
    return re.sub(r"[-\s]+", "-", cleaned)


@router.get(
    "",
    response_model=ProjectListResponse,
    summary="List projects with resource counts",
)
def list_projects(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    search: str | None = Query(default=None, description="Search by name or slug"),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    query = select(Project)
    if search:
        s = f"%{search.strip()}%"
        query = query.where((Project.name.ilike(s)) | (Project.slug.ilike(s)))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    projects = db.scalars(
        query.order_by(Project.created_at.desc()).limit(limit).offset(offset)
    ).all()

    items = []
    for p in projects:
        a_count = db.scalar(
            select(func.count()).where(AssistantVersion.project_id == p.id)
        ) or 0
        d_count = db.scalar(
            select(func.count()).where(Dataset.project_id == p.id)
        ) or 0
        r_count = db.scalar(
            select(func.count()).where(EvaluationRun.project_id == p.id)
        ) or 0

        items.append(
            ProjectResponse(
                id=p.id,
                name=p.name,
                slug=p.slug,
                description=p.description,
                assistants_count=a_count,
                datasets_count=d_count,
                runs_count=r_count,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
        )

    return ProjectListResponse(items=items, total=total)


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    slug = payload.slug.strip() if payload.slug else _slugify(payload.name)
    if not slug:
        slug = f"project-{uuid.uuid4().hex[:6]}"

    # Check slug collision
    existing = db.scalar(select(Project).where(Project.slug == slug))
    if existing:
        slug = f"{slug}-{uuid.uuid4().hex[:4]}"

    project = Project(
        name=payload.name.strip(),
        slug=slug,
        description=payload.description.strip() if payload.description else None,
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        assistants_count=0,
        datasets_count=0,
        runs_count=0,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Get project details by ID",
)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    a_count = db.scalar(select(func.count()).where(AssistantVersion.project_id == project.id)) or 0
    d_count = db.scalar(select(func.count()).where(Dataset.project_id == project.id)) or 0
    r_count = db.scalar(select(func.count()).where(EvaluationRun.project_id == project.id)) or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        assistants_count=a_count,
        datasets_count=d_count,
        runs_count=r_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
    summary="Update project name and description",
)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
) -> ProjectResponse:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Project '{project_id}' not found.",
        )

    if payload.name is not None:
        project.name = payload.name.strip()
    if payload.description is not None:
        project.description = payload.description.strip()

    db.commit()
    db.refresh(project)

    a_count = db.scalar(select(func.count()).where(AssistantVersion.project_id == project.id)) or 0
    d_count = db.scalar(select(func.count()).where(Dataset.project_id == project.id)) or 0
    r_count = db.scalar(select(func.count()).where(EvaluationRun.project_id == project.id)) or 0

    return ProjectResponse(
        id=project.id,
        name=project.name,
        slug=project.slug,
        description=project.description,
        assistants_count=a_count,
        datasets_count=d_count,
        runs_count=r_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )

