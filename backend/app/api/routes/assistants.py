"""FastAPI endpoints for AssistantVersion management."""

import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.assistant_version import AssistantVersion
from app.models.evaluation_run import EvaluationRun
from app.models.project import Project
from app.schemas.assistant import (
    AssistantVersionCreate,
    AssistantVersionListResponse,
    AssistantVersionResponse,
)

router = APIRouter()


@router.get(
    "",
    response_model=AssistantVersionListResponse,
    summary="List assistant versions",
)
def list_assistants(
    project_id: uuid.UUID | None = Query(default=None, description="Filter by project UUID"),
    search: str | None = Query(default=None, description="Search by assistant name or model"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> AssistantVersionListResponse:
    query = select(AssistantVersion).options(joinedload(AssistantVersion.project))

    if project_id:
        query = query.where(AssistantVersion.project_id == project_id)
    if search:
        s = f"%{search.strip()}%"
        query = query.where(
            (AssistantVersion.name.ilike(s)) | (AssistantVersion.model_name.ilike(s))
        )

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    assistants = db.scalars(
        query.order_by(AssistantVersion.created_at.desc()).limit(limit).offset(offset)
    ).unique().all()

    items = []
    for a in assistants:
        r_count = db.scalar(
            select(func.count()).where(EvaluationRun.assistant_version_id == a.id)
        ) or 0
        items.append(
            AssistantVersionResponse(
                id=a.id,
                project_id=a.project_id,
                project_name=a.project.name if a.project else None,
                name=a.name,
                version=a.version,
                provider=a.provider,
                model_name=a.model_name,
                system_prompt=a.system_prompt,
                config=a.config,
                runs_count=r_count,
                created_at=a.created_at,
            )
        )

    return AssistantVersionListResponse(items=items, total=total)


@router.post(
    "",
    response_model=AssistantVersionResponse,
    status_code=http_status.HTTP_201_CREATED,
    summary="Register a new assistant version",
)
def create_assistant(
    payload: AssistantVersionCreate,
    db: Session = Depends(get_db),
) -> AssistantVersionResponse:
    project = db.get(Project, payload.project_id)
    if not project:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Project '{payload.project_id}' does not exist.",
        )

    # Check unique version for project
    existing = db.scalar(
        select(AssistantVersion).where(
            AssistantVersion.project_id == payload.project_id,
            AssistantVersion.version == payload.version.strip(),
        )
    )
    if existing:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Assistant version '{payload.version}' already exists for this project.",
        )

    av = AssistantVersion(
        project_id=payload.project_id,
        name=payload.name.strip(),
        version=payload.version.strip(),
        provider=payload.provider.strip() if payload.provider else "mock",
        model_name=payload.model_name.strip() if payload.model_name else "mock-model",
        system_prompt=payload.system_prompt.strip() if payload.system_prompt else None,
        config=payload.config or {},
    )
    db.add(av)
    db.commit()
    db.refresh(av)

    return AssistantVersionResponse(
        id=av.id,
        project_id=av.project_id,
        project_name=project.name,
        name=av.name,
        version=av.version,
        provider=av.provider,
        model_name=av.model_name,
        system_prompt=av.system_prompt,
        config=av.config,
        runs_count=0,
        created_at=av.created_at,
    )


@router.get(
    "/{assistant_id}",
    response_model=AssistantVersionResponse,
    summary="Get assistant version details by ID",
)
def get_assistant(
    assistant_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> AssistantVersionResponse:
    av = db.scalar(
        select(AssistantVersion)
        .options(joinedload(AssistantVersion.project))
        .where(AssistantVersion.id == assistant_id)
    )
    if not av:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"AssistantVersion '{assistant_id}' not found.",
        )

    r_count = db.scalar(
        select(func.count()).where(EvaluationRun.assistant_version_id == av.id)
    ) or 0

    return AssistantVersionResponse(
        id=av.id,
        project_id=av.project_id,
        project_name=av.project.name if av.project else None,
        name=av.name,
        version=av.version,
        provider=av.provider,
        model_name=av.model_name,
        system_prompt=av.system_prompt,
        config=av.config,
        runs_count=r_count,
        created_at=av.created_at,
    )

