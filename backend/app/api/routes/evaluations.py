"""FastAPI endpoints for managing and inspecting evaluation runs."""

import logging
from typing import Annotated
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status as http_status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.evaluation.comparison import compare_evaluation_runs
from app.evaluation.exceptions import (
    ComparisonError,
    EvaluationConfigError,
    IncompatibleProjectError,
)
from app.evaluation.orchestrator import create_evaluation_run, execute_evaluation_run
from app.evaluation.promptfoo import execute_promptfoo_evaluation
from app.evaluation.quality_gate import evaluate_release_quality_gate
from app.models.assistant_version import AssistantVersion
from app.models.case_result import CaseResult
from app.models.evaluation_run import EvaluationRun
from app.schemas.comparison import ComparisonRequest, ComparisonResponse
from app.schemas.evaluation import (
    CaseResultListResponse,
    CaseResultResponse,
    EvaluationCreateRequest,
    EvaluationRunListResponse,
    EvaluationRunResponse,
)
from app.schemas.promptfoo import (
    PromptfooEvaluationRequest,
    PromptfooEvaluationResponse,
)
from app.schemas.quality_gate import QualityGateRequest, QualityGateResponse

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


@router.post(
    "/promptfoo",
    response_model=PromptfooEvaluationResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Execute Promptfoo prompt and adversarial test suite",
)
async def evaluate_with_promptfoo(
    payload: PromptfooEvaluationRequest,
    db: Session = Depends(get_db),
) -> PromptfooEvaluationResponse:
    """Execute the Promptfoo CLI suite against a target assistant version."""
    assistant_name = None
    assistant_version_str = payload.version

    if payload.assistant_version_id is not None:
        av = db.get(AssistantVersion, payload.assistant_version_id)
        if av is None:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"AssistantVersion '{payload.assistant_version_id}' not found.",
            )
        assistant_name = av.name
        assistant_version_str = av.version

    response = await execute_promptfoo_evaluation(
        assistant_version_id=payload.assistant_version_id,
        version=payload.version,
        provider=payload.provider,
        timeout_seconds=payload.timeout_seconds,
        assistant_name=assistant_name,
        assistant_version=assistant_version_str,
    )

    return response


@router.post(
    "/compare",
    response_model=ComparisonResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Compare two completed evaluation runs",
)
def compare_evaluations(
    payload: ComparisonRequest,
    db: Session = Depends(get_db),
) -> ComparisonResponse:
    """Compare performance, metrics, regressions, and latency between two completed runs."""
    try:
        return compare_evaluation_runs(
            db=db,
            baseline_run_id=payload.baseline_run_id,
            candidate_run_id=payload.candidate_run_id,
        )
    except (ComparisonError, IncompatibleProjectError) as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except EvaluationConfigError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.post(
    "/release-gate",
    response_model=QualityGateResponse,
    status_code=http_status.HTTP_200_OK,
    summary="Evaluate candidate assistant version release quality gate",
)
def evaluate_quality_gate(
    payload: QualityGateRequest,
    db: Session = Depends(get_db),
) -> QualityGateResponse:
    """Evaluate candidate assistant version against release quality criteria and return PASS/FAIL."""
    try:
        return evaluate_release_quality_gate(
            db=db,
            baseline_run_id=payload.baseline_run_id,
            candidate_run_id=payload.candidate_run_id,
            thresholds=payload.thresholds,
        )
    except (ComparisonError, IncompatibleProjectError) as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except EvaluationConfigError as e:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


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
        query.options(
            joinedload(EvaluationRun.project),
            joinedload(EvaluationRun.assistant_version),
            joinedload(EvaluationRun.dataset),
        )
        .order_by(EvaluationRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    ).unique().all()

    response_items = []
    for run in items:
        pr = round((run.passed_cases / run.total_cases * 100.0), 1) if run.total_cases > 0 else 0.0
        response_items.append(
            EvaluationRunResponse(
                id=run.id,
                project_id=run.project_id,
                assistant_version_id=run.assistant_version_id,
                dataset_id=run.dataset_id,
                status=run.status,
                total_cases=run.total_cases,
                passed_cases=run.passed_cases,
                failed_cases=run.failed_cases,
                config=run.config,
                project_name=run.project.name if run.project else None,
                assistant_name=run.assistant_version.name if run.assistant_version else None,
                assistant_version_tag=run.assistant_version.version if run.assistant_version else None,
                dataset_name=run.dataset.name if run.dataset else None,
                pass_rate=pr,
                started_at=run.started_at,
                completed_at=run.completed_at,
                created_at=run.created_at,
            )
        )

    return EvaluationRunListResponse(
        items=response_items,
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
) -> EvaluationRunResponse:
    """Fetch status, case counts, and execution metadata for a specific evaluation run."""
    run = db.scalar(
        select(EvaluationRun)
        .options(
            joinedload(EvaluationRun.project),
            joinedload(EvaluationRun.assistant_version),
            joinedload(EvaluationRun.dataset),
        )
        .where(EvaluationRun.id == run_id)
    )
    if not run:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=f"Evaluation run '{run_id}' not found.",
        )
    pr = round((run.passed_cases / run.total_cases * 100.0), 1) if run.total_cases > 0 else 0.0
    return EvaluationRunResponse(
        id=run.id,
        project_id=run.project_id,
        assistant_version_id=run.assistant_version_id,
        dataset_id=run.dataset_id,
        status=run.status,
        total_cases=run.total_cases,
        passed_cases=run.passed_cases,
        failed_cases=run.failed_cases,
        config=run.config,
        project_name=run.project.name if run.project else None,
        assistant_name=run.assistant_version.name if run.assistant_version else None,
        assistant_version_tag=run.assistant_version.version if run.assistant_version else None,
        dataset_name=run.dataset.name if run.dataset else None,
        pass_rate=pr,
        started_at=run.started_at,
        completed_at=run.completed_at,
        created_at=run.created_at,
    )


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


