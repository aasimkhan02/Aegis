"""FastAPI endpoints for managing and inspecting evaluation runs."""

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.evaluation.exceptions import EvaluationConfigError, IncompatibleProjectError
from app.evaluation.orchestrator import create_evaluation_run, execute_evaluation_run
from app.models.case_result import CaseResult
from app.models.evaluation_run import EvaluationRun
from app.schemas.evaluation import (
    CaseResultListResponse,
    CaseResultResponse,
    EvaluationCreateRequest,
    EvaluationRunListResponse,
    EvaluationRunResponse,
)

logger = logging.getLogger("aegis.api.evaluations")
router = APIRouter()


@router.post(
    "",
    response_model=EvaluationRunResponse,
    status_code=http_status.HTTP_202_ACCEPTED,
    summary="Start an evaluation run",
)
def start_evaluation(
    payload: EvaluationCreateRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> EvaluationRun:
    """Validate parameters, create a pending EvaluationRun, and dispatch background execution."""
    try:
        eval_run = create_evaluation_run(
            db=db,
            assistant_version_id=payload.assistant_version_id,
            dataset_id=payload.dataset_id,
            config=payload.config.model_dump(),
        )
    except IncompatibleProjectError as e:
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=str(e),
        )
    except EvaluationConfigError as e:
        if "not found" in str(e).lower() or "does not exist" in str(e).lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )

    # Schedule asynchronous execution in background task (uses isolated DB sessions)
    background_tasks.add_task(
        execute_evaluation_run,
        evaluation_run_id=eval_run.id,
        max_concurrency=payload.config.max_concurrency,
        fail_fast=payload.config.fail_fast,
    )

    return eval_run


@router.get(
    "",
    response_model=EvaluationRunListResponse,
    summary="List evaluation runs",
)
def list_evaluations(
    project_id: uuid.UUID | None = Query(default=None, description="Filter by project UUID"),
    dataset_id: uuid.UUID | None = Query(default=None, description="Filter by dataset UUID"),
    assistant_version_id: uuid.UUID | None = Query(default=None, description="Filter by assistant version UUID"),
    run_status: str | None = Query(default=None, alias="status", description="Filter by status (pending, running, completed, failed)"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> EvaluationRunListResponse:
    """Retrieve paginated evaluation runs matching optional filters."""
    query = select(EvaluationRun)

    if project_id:
        query = query.where(EvaluationRun.project_id == project_id)
    if dataset_id:
        query = query.where(EvaluationRun.dataset_id == dataset_id)
    if assistant_version_id:
        query = query.where(EvaluationRun.assistant_version_id == assistant_version_id)
    if run_status:
        query = query.where(EvaluationRun.status == run_status.lower().strip())

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.order_by(EvaluationRun.created_at.desc()).limit(limit).offset(offset)
    ).all()

    return EvaluationRunListResponse(
        items=list(items),
        total=total,
    )


@router.get(
    "/{run_id}",
    response_model=EvaluationRunResponse,
    summary="Get evaluation run details",
)
def get_evaluation(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> EvaluationRun:
    """Fetch status, case counts, and execution metadata for a specific evaluation run."""
    run = db.scalar(
        select(EvaluationRun).where(EvaluationRun.id == run_id)
    )
    if not run:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found.",
        )
    return run


@router.get(
    "/{run_id}/results",
    response_model=CaseResultListResponse,
    summary="List case results for an evaluation run",
)
def list_case_results(
    run_id: uuid.UUID,
    case_status: str | None = Query(default=None, alias="status", description="Filter by case status (passed, failed, error)"),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> CaseResultListResponse:
    """Fetch paginated case results and their nested metrics for an evaluation run."""
    run = db.scalar(select(EvaluationRun.id).where(EvaluationRun.id == run_id))
    if not run:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found.",
        )

    query = select(CaseResult).where(CaseResult.evaluation_run_id == run_id)
    if case_status:
        query = query.where(CaseResult.status == case_status.lower().strip())

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = db.scalars(
        query.options(joinedload(CaseResult.metric_results))
        .order_by(CaseResult.created_at.asc())
        .limit(limit)
        .offset(offset)
    ).unique().all()

    return CaseResultListResponse(
        items=list(items),
        total=total,
    )


@router.get(
    "/{run_id}/results/{result_id}",
    response_model=CaseResultResponse,
    summary="Get single case result details",
)
def get_case_result(
    run_id: uuid.UUID,
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
) -> CaseResult:
    """Fetch complete snapshot, output, and metrics for a specific case result."""
    result = db.scalar(
        select(CaseResult)
        .options(joinedload(CaseResult.metric_results))
        .where(
            CaseResult.evaluation_run_id == run_id,
            CaseResult.id == result_id,
        )
    )
    if not result:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Case result '{result_id}' for evaluation run '{run_id}' not found.",
        )
    return result
